##getConfig Function
import json
import boto3
import os

ssm=boto3.client('ssm')

def lambda_handler(event, context):
    BLASTER_DEPLOYMENT = os.environ['BLASTER_DEPLOYMENT']
    config=get_parameters(BLASTER_DEPLOYMENT)
    config['dialerThreads']= [0]*config['concurrentCalls']
    return config
    
def get_parameters(deployment):
    
    config={}
    next_token = None

    try:
        while True:
            if next_token:
                ssmresponse = ssm.get_parameters_by_path(Path='/connect/blaster/'+deployment+'/',NextToken=next_token)
            else:
                ssmresponse = ssm.get_parameters_by_path(Path='/connect/blaster/'+deployment+'/')
            for parameter in ssmresponse['Parameters']:
                if(parameter['Value'].isnumeric()):
                   config[parameter['Name'].split("/")[-1]]=int(parameter['Value'])
                else:
                   config[parameter['Name'].split("/")[-1]]=parameter['Value']
            next_token = ssmresponse.get('NextToken')

            if not next_token:
                break

    except:
        print("Error getting config")
        return None
    else:
        return config
