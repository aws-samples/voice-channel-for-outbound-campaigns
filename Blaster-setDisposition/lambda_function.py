##setDisposition Function
import json
import boto3
import os
from blaster import update_dial_list, save_results

connect=boto3.client('connect')
BLASTER_DEPLOYMENT = os.environ['BLASTER_DEPLOYMENT']
RESULTS_FIREHOSE_NAME = os.environ['RESULTS_FIREHOSE_NAME']

def lambda_handler(event, context):
    print(event)

    contactId = event['Details']['ContactData'].get('InitialContactId',False)
    phone=event['Details']['ContactData'].get('CustomerEndpoint',False)
    
    
    results = {'CampaignStep':'CallCompleted','phone':phone,'contactId':contactId}
    
    if('Attributes' in event['Details']['ContactData'] and len(event['Details']['ContactData']['Attributes'])>0):
        for attkey in event['Details']['ContactData']['Attributes'].keys():
            results.update({attkey:event['Details']['ContactData']['Attributes'][attkey]})
    
    save_results(results,BLASTER_DEPLOYMENT,RESULTS_FIREHOSE_NAME)
    
    '''
    #instanceArn= event['Details']['ContactData']['InstanceARN']
    #instanceId=instanceArn.split("/")[-1]

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
    '''
    return {
        'Saved': True
        } 
