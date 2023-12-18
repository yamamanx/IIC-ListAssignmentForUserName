import json
import boto3
import logging

id_store = boto3.client('identitystore')
sso_admin = boto3.client('sso-admin')
logger = logging.getLogger()
account_assignments = []
application_assignments = []


def get_principal_id(id_store_id, user_name):
    response = id_store.get_user_id(
        IdentityStoreId=id_store_id,
        AlternateIdentifier={
            'UniqueAttribute': {
                'AttributePath': 'userName',
                'AttributeValue': user_name
            }
        }
    )
    return response['UserId']
    
    
def get_group_id(id_store_id, user_id):
    response = id_store.list_group_memberships_for_member(
        IdentityStoreId=id_store_id,
        MemberId={
            'UserId': user_id
        }
    )
    group_ids = []
    if len(response['GroupMemberships']) > 0:
        for group_menmber_ship in response['GroupMemberships']:
            group_ids.append(group_menmber_ship['GroupId'])
    return group_ids
    
    
def append_account_assignments(instance_arn, principal_id,principal_type):
    response = sso_admin.list_account_assignments_for_principal(
        InstanceArn=instance_arn,
        PrincipalId=principal_id,
        PrincipalType=principal_type
    )
    if len(response['AccountAssignments']) > 0:
        for account_assignment in response['AccountAssignments']:
            permission_set_name = get_permission_set_name(instance_arn, account_assignment['PermissionSetArn'])
            account_assignments.append(
                {
                    "AccountId": account_assignment['AccountId'],
                    "PermissionSetName": permission_set_name
                }
            )
            

def get_permission_set_name(instance_arn, permission_set_arn):
    response = sso_admin.describe_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=permission_set_arn
    )
    return response['PermissionSet']['Name']
    
    
def append_application_assignments(instance_arn, principal_id,principal_type):
    response = sso_admin.list_application_assignments_for_principal(
        InstanceArn=instance_arn,
        PrincipalId=principal_id,
        PrincipalType=principal_type
    )
    if len(response['ApplicationAssignments']) > 0:
        for application_assignment in response['ApplicationAssignments']:
            application_name = get_application_name(application_assignment['ApplicationArn'])
            application_assignments.append(
                {
                    "ApplicationName": application_name
                }
            )
            

def get_application_name(application_arn):
    response = sso_admin.describe_application(
        ApplicationArn=application_arn
    )
    return response['Name']


def lambda_handler(event, context):
    id_store_id = event['IdStoreId']
    user_name = event['UserName']
    instance_arn = event['InstanceArn']
    
    user_id = get_principal_id(id_store_id, user_name)
    append_account_assignments(instance_arn, user_id, 'USER')
    append_application_assignments(instance_arn, user_id, 'USER')
    
    group_ids = get_group_id(id_store_id, user_id)
    if len(group_ids) > 0:
        for group_id in group_ids:
            append_account_assignments(instance_arn, group_id, 'GROUP')
            append_application_assignments(instance_arn, group_id, 'GROUP')
    
    response = {
        'UserId': user_id,
        'GroupIds': group_ids,
        'AccountAssignments': account_assignments,
        'ApplicationAssignments': application_assignments
    }
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }

