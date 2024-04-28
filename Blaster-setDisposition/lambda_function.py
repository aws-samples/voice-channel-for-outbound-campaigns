##setDisposition Function
import json
import boto3
import os
from blaster import update_dial_list, save_results

connect=boto3.client('connect')

def lambda_handler(event, context):
    BLASTER_DEPLOYMENT = os.environ['BLASTER_DEPLOYMENT']
    RESULTS_FIREHOSE_NAME = os.environ['RESULTS_FIREHOSE_NAME']
    
    print(event)
    contactId = event['Details']['ContactData']['Attributes'].get('contactId',False)
    
    instanceArn= event['Details']['ContactData']['InstanceARN']
    dispositionCode= event['Details']['ContactData']['Attributes'].get('dispositionCode',False)
    phone=event['Details']['ContactData']['Attributes'].get('phone',False)
    
    instanceId=instanceArn.split("/")[-1]
    results = {'CampaignStep':'CallCompleted','phone':phone,'contactId':contactId,'dispositionCode':dispositionCode}
    save_results(results,BLASTER_DEPLOYMENT,RESULTS_FIREHOSE_NAME)
    
    if(contactId and dispositionCode):
        response = connect.update_contact_attributes(
        InitialContactId=contactId,
        InstanceId=instanceId,
        Attributes={
            'disposition-code': dispositionCode
        }
        )
        return {
        'Tagged': True
        }
    return {
        'Tagged': False
        } 
