import boto3
import logging, os, json
from base64 import b64decode
from re import search
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

#Update following variables 
SLACK_WEBHOOK_URL=os.environ['SLACK_WEB_HOOK_DETAILS']
SLACK_CHANNEL_NAME=os.environ['CHANNEL_NAME']
SLACK_USERNAME=os.environ['USER_NAME']
SLACK_ICON_EMOJI=':robot_face:'

#Update AWS Details 
AWS_REGION = os.environ['REGION']
HostedZoneId = os.environ['HOSTED_ZONE_ID']
Clientvpnendpoint = os.environ['VPN_ENDPOINT_ID']
Sub_domain_name = os.environ['SUB_DOMAIN']


client = boto3.client('ec2', region_name=AWS_REGION)
# ec2 = boto3.client('ec2')
#Logging Variables
logger = logging.getLogger()
logger.setLevel(logging.INFO)

#Slack Message function
def lambda_to_slack(SLACK_MSG):
    payload = {'text':SLACK_MSG,'channel':SLACK_CHANNEL_NAME,'icon_emoji':SLACK_ICON_EMOJI,'username':SLACK_USERNAME}
    print('Sending Message to Slack')
    req = Request(SLACK_WEBHOOK_URL, json.dumps(payload).encode('utf-8'))
    try:
        response = urlopen(req)
        response.read()
        logger.info("Message posted to %s", payload['channel'])
    except HTTPError as e:
        logger.error("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        logger.error("Server connection failed: %s", e.reason)
    return 0


rout353client = boto3.client('route53')
response = client.describe_client_vpn_connections(
    ClientVpnEndpointId=Clientvpnendpoint
)
print(response)
def lambda_handler(event, context):
    length = len(response["Connections"])
    print("length", length)
    client_IpAddress = []
    commonName = []
    for i in range(length):
        if (response["Connections"][i]["Status"]["Code"]) == "active":
            client_IpAddress = response["Connections"][i]["ClientIp"]
            commonName = response["Connections"][i]["CommonName"]
            #print(client_IpAddress, commonName)
            subdomain = Sub_domain_name
            if search(subdomain, commonName):
                route53response = rout353client.change_resource_record_sets(
                    ChangeBatch={
                        'Changes': [
                            {
                                'Action': 'UPSERT',
                                'ResourceRecordSet': {
                                    'Name': commonName,
                                    'Type': 'A',
                                    'TTL': 300,
                                    'ResourceRecords': [
                                        {
                                            'Value': client_IpAddress
                                        },
                                    ],
                                },
                            },
                        ],
                        'Comment': 'VPN Client End point',
                    },
                    HostedZoneId=HostedZoneId,
                )
                print(route53response)
                #print('bucketname:{},response: {}'.format(s3bucketname, response))
                lambda_to_slack('IpAddress:{},  DomainName: {}'.format(client_IpAddress,commonName))
