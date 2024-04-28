# Voice channel for outbound campaigns
This project contains source code and supporting files for implementing Amazon Connect as a voice channel for Amazon Pinpoint.

Campaigns are orchestrated by Amazon Pinpoint with a custom channel. An AWS Stepfunction state machine controls the dialing pace by triggering startoutboundvoicecall calls at the concurrency required.

The general process for the operation is as follows:

1. The administrator loads segments on Amazon Pinpoint based on schema the file in the sample-files folder. Required attributes should be placed at the User.UserAttributes level.
2. The administrator creates a voice message template in Amazon Pinpoint with the attributes available in the targeted segment.
3. The administrator creates a campaign with a custom channel (using the queueContacts function), the required segment and the intended message template as part of the DATA entered when selecting the AWS Lambda Function.
4. The solution validates each endpoint based on the destination country prefix provided during setup using pinpoint Phone Number Validate and queues valid contact on an SQS queue. Finally, after queueing contacts, a StepFunctions state machine is started.
5. The state machine pulls configuration from Systems Manager Parameter Store path /connect/blaster/XXX/. This includes connect configuration (Connect instance ID, Queue Id, Contact flow Id) and dialing behaviour configuration (concurrent calls and predefined timeouts).
6. The state machine pulls contacts from the Dialing list table based on the concurrency parameter an launched mapped executions to run simultaneous threads.
7.	Successful call connections are put in queue with the predefined contact flow. Contact flows can be prebuilt as blaster mode (only providing a prompt and disconnecting the call) or blaster with interactions with bots or agents. New calls are only placed until the initial call is completed or the timeout parameter is expired.

## Deployed resources

The project includes a cloud formation template with a Serverless Application Model (SAM) transform to deploy resources as follows:

### S3 Buckets
- InputBucket: Used for list loading based on CSV files (Refer to the sample files for the structure). Fields custID and phone are mandatory. Additional fields are populated as attributes while placing calls. This is only optional and using Pinpoint is highly recommended.
- Resultsbucket: Storage for campaign results.

### AWS Lambda functions

- queueContacts: Receives events from Amazon Pinpoint and puts them on the SQS queue.
- dial: Places calls using Amazon Connect boto3's start_outbound_voice_contact method.
- getConfig: Gets the configuration parameters from Systems Manager Parameter store.
- getContacts: Gets contacts from the queue.
- ProcessContactEvents: Processes Contact Events to determine when would the next call should be placed.
- SetDisposition: Process agent input based on a step by step guide contact flow to categorize calls.

### Step Functions
- DialerControlSF: Provides the general structure for the dialer. Pulls initial configuration and creates parallel executions to perform the dialing process.

### DynamoDB
- ActiveDialing: ContactIds to dialed contact relationship for contacts being dialed.

### System Manager Paramater Store Parameters
Configuration information is stored as parameters in System Manager Parameter Store. The following parameters require configuration to match Connect configuration.
- /connect/blaster/XXXX/connectid. Connect Instance Id (not ARN).
- /connect/blaster/XXXX/contactflow. Contact Flow Id (not ARN).
- /connect/blaster/XXXX/queue. Amazon Connect Outbound Queue (not ARN).

- /connect/blaster/XXXX/countrycode. Numeric country code.
- /connect/blaster/XXXX/isocountrycode. 2 letters ISO country code.
- /connect/blaster/XXXX/concurrentcalls. Concurrent dialers to launch activity.
- /connect/blaster/XXXX/timeOut. Concurrent dialers to launch activity.

- /connect/blaster/XXXX/ResultsBucket. Output bucket for results. Populated at set up time.
- /connect/blaster/XXXX/activeBlaster. On/Off switch for dialer opperation. Managed by State machines.
- /connect/blaster/XXXX/dialIndex. index position within list.
- /connect/blaster/XXXX/table-activedialing. Active numbers processing calls.
- /connect/blaster/XXXX/totalRecords. Current number of records to be called.

### IAM roles
- ControlSFRole: Dialer Control Step Functions state Machine IAM role.
- BlasterLambdaRole: Lambda Functions IAM role.

## Prerequisites.
1. Amazon Connect Instance already set up with corresponding queue and contact flows.
2. AWS Console Access with administrator account.
3. Acces to AWS Cloudshell.

## Deploy the solution
1. Clone this repo.

`git clone https://github.com/aws-samples/voice-channel-for-outbound-campaigns`

2. Build the solution with SAM.

`sam build` 


3. Deploy the solution.

`sam deploy -g`

SAM will ask for the name of the application (use "blaster" or something similar) as all resources will be grouped under it; Region and a confirmation prompt before deploying resources, enter y.
SAM can save this information if you plan un doing changes, answer Y when prompted and accept the default environment and file name for the configuration.


## Configure Amazon Connect Agent Events and Contact Trace Records.

## Get Amazon Connect Configuration

As part of the configuration, you will need the deployed Amazon Connect information: Instance ID (referenced as connectid on the configuration parameters of this solution), a contact flow used for Outbound calling (referenced as contactflow on the configuration parameters of this solution), queue ID (referenced as queue).

1. Navigate to the Amazon Connect console.
2. Click on Access URL. This will open the Amazon Connect interface.
3. From the left panel, open the routing menu (it has an arrow splitting in three as an icon).
4. Click on contact flow. Select the Default outbound contact flow. Click on "show additional flow information".
5. Copy the associated ARN. You will need 2 items from that string the instance id and the contact flow id. The instance ID is the string following the first "/" after the word instance and up to the following "/".The contact flow ID is the string separated by the "/" following "contact-flow". Make note of this 2 strings (do not copy "/").
6. Navigate back to routing and pick queues. Select the queue you'll be using and click on show additional queue information.
7. Make note of the string separated by a "/" after the word queue on the ARN. Make sure you do not copy "/".


## Configure Parameters
All required parameters to be configured are asked at deployment time, but changes can be done directly in the associated parameters:

1. Navigate to the System Manager - Parameter Store console.
2. Modify the values for the following items . Note this items are case sensitive.

| parameter   | currentValue |
|----------|:-------------:|
| /connect/blaster/XXXX/connectid |  Connect instance ID |
| /connect/blaster/XXXX/contactflow |contactflow ID|
|/connect/blaster/XXXX/concurrentcalls|Number of concurrent calls to be launched|
|/connect/blaster/XXXX/timeOut|Number of seconds to wait for the calls to be terminated before forcing a new call (Should be larger than the expected duration to avoid starting new calls ahead of availability)|

## Setting Disposition Codes
As part of the deployment, a setDisposition Code function is created. This function will take contactId and attributes set on the dial phase to update the result on the dialing list table.
The step by step guide contact flow (file , available on the sample files allows for a sample option to generate status and invoke the setDisposition Lambda function to tag associated contacts.

### Deploy agent guide flow.
1. From the AWS Services Console, browse to the Amazon Connect service and add the setDisposition Lambda function in Flows->Lambda.
1. In the Amazon Connect administrator interface create a new contact flow and import the View-Dialer-DispositionCodes sample file. Validate all boxes are configured correctly, save and publish the flow.
1. Make a note of the contact flow id on the ARN for this contact flow.
1. Add a Set Contact Attributes block on the ContactFlow used for outbound calls, specify a user defined parameter for DefaultFlowForAgentUI and specify the contact flow id from the previous step.

## Operation
The solution relies on Step Functions as the main orchestation point and Lambda Functions as the processing units. To start a campaign:
1. Create a segment and a VOICE message template in Pinpoint.
2. Launch a new CUSTOM campaign with the queueContacts lambda function as a destination.

### Controlling campaign schedules
Campaigns are matched with Amazon Connect queue's hours of operation and will stop generating new calls when outside of working hours. Queue status is also monitored and can be used to forcefully stop an ongoing campaign by disabling said queue. The campaign will not restart if the queue is enabled, nevertheless.

SQS queue will hold the contacts for 24 hours and then purge them. Launching a new Pinpoint campaign will trigger the campaing launch.

### Stopping a  dialing job
To forcefully stop a state machine outside of Amazon Connect, got to Systems Manager Parameter Store and change the parameter /connect/dialer/XXXX/activeBlaster to False.

### About the inner workings.
1. The state machine will iterate over the dialing list, pulling contacts as previous calls are completed. Bear in mind the eventbridge disconnect events are monitored to determine when a new call is required.
2. The StepFunction machine will create dialing threads based on the concurrent calls parameter by the time the process starts. This dialing workers fetch contacts from the dialing list, place calls and wait for calls to be completed or timeout to expire to iterate over a new contact. The recommended relation concurrent calls is 1:1 for the number of maximum supported calls on the Amazon Connect instance and should be 1:1 to agents if interactivity is expected.
3. Once a dialing worker reaches the end of the list, the activeBlaster paramter is set to false in the dialer configuration parameters. This stops all subsequent fetching attempts and finalizes the dialing process. You can manually set the activeDialer attribute to false to stop the dialing process.


## Resource deletion
1. Remove any folders from the iobucket. You can browse to the S3 bucket (click on CloudFormation iobucket link on the resources tab for this stack), select all objects and click on delete.
2. Back on the cloudformation console, select the stack and click on Delete and confirm it by pressing Delete Stack. 
