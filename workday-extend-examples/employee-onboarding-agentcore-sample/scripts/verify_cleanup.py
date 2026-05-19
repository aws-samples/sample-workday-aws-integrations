#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Verification script to check whether the resources this sample's deploy.sh
creates have been cleaned up.

Discovery strategy mirrors complete_cleanup.sh:
- Exact name / path match for resources we own by name.
- Unique-agent-name substring for toolkit-auto-created resources.
- Tag-based check for resources we tag (Cognito user pool, S3 buckets).
- The account-wide shared S3 build bucket and service-linked role are
  deliberately NOT checked — they're expected to survive cleanup.
"""

import boto3
import sys
import os
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Tuple

# Sample identity (must match deploy.sh and complete_cleanup.sh)
SAMPLE_ID = "sample-amazon-bedrock-agentcore-employee-onboarding"
RESOURCE_PREFIX = "bedrock-employee-onboarding"
RESOURCE_PREFIX_UNDERSCORE = "bedrock_employee_onboarding"
AGENT_NAME = "employee_onboarding"
IAM_PATH = f"/{RESOURCE_PREFIX}/"
SAMPLE_TAG_KEY = "Sample"
SAMPLE_TAG_VALUE = SAMPLE_ID

# Names we deliberately skip cleaning up (see SECURITY.md)
SKIP_S3_BUCKET_PREFIX = "bedrock-agentcore-codebuild-sources-"
SKIP_SLR_NAME = "AWSServiceRoleForBedrockAgentCoreRuntimeIdentity"

class CleanupVerifier:
    """Verifies that all AgentCore resources have been properly cleaned up."""
    
    def __init__(self):
        """Initialize the verifier with AWS session."""
        try:
            self.session = boto3.Session(region_name='us-east-1')
            # Test credentials
            sts = self.session.client('sts')
            self.account_id = sts.get_caller_identity()['Account']
            print(f"🔍 Verifying cleanup for AWS Account: {self.account_id}")
        except NoCredentialsError:
            print("❌ AWS credentials not configured. Please run 'aws configure'")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error initializing AWS session: {e}")
            sys.exit(1)
    
    def print_section(self, title: str):
        """Print a section header."""
        print(f"\n{title}")
        print("=" * len(title))
    
    def print_status(self, message: str, success: bool = True):
        """Print a status message with appropriate icon."""
        icon = "✅" if success else "❌"
        print(f"{icon} {message}")
    
    def print_warning(self, message: str):
        """Print a warning message."""
        print(f"⚠️  {message}")
    
    def print_info(self, message: str):
        """Print an info message."""
        print(f"ℹ️  {message}")
    
    def check_agent_runtimes(self) -> Tuple[bool, List[str]]:
        """Check for remaining Bedrock AgentCore runtime registrations for this sample."""
        try:
            control = self.session.client('bedrock-agentcore-control')
            runtimes = control.list_agent_runtimes().get('agentRuntimes', [])
            sample_runtimes = [
                f"{r.get('agentRuntimeName')} ({r.get('agentRuntimeId')})"
                for r in runtimes
                if (r.get('agentRuntimeName') or '') == AGENT_NAME
            ]

            if sample_runtimes:
                self.print_status(f"Found {len(sample_runtimes)} runtime(s) named '{AGENT_NAME}'", False)
                for rt in sample_runtimes:
                    print(f"   - {rt}")
                return False, sample_runtimes
            else:
                self.print_status(f"No AgentCore runtime named '{AGENT_NAME}' found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking AgentCore runtimes: {e}")
            return False, [f"Error: {e}"]

    def check_agentcore_gateways(self) -> Tuple[bool, List[str]]:
        """Check for remaining AgentCore Gateways matching this sample's name prefix."""
        try:
            control = self.session.client('bedrock-agentcore-control')
            resp = control.list_gateways()
            gateways = resp.get('items', [])
            sample_gateways = [
                f"{gw.get('name')} ({gw.get('gatewayId')})"
                for gw in gateways
                if (gw.get('name') or '').startswith(RESOURCE_PREFIX)
            ]

            if sample_gateways:
                self.print_status(f"Found {len(sample_gateways)} gateway(s) for this sample", False)
                for gw in sample_gateways:
                    print(f"   - {gw}")
                return False, sample_gateways
            else:
                self.print_status("No AgentCore Gateways for this sample found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking AgentCore gateways: {e}")
            return False, [f"Error: {e}"]

    def check_agentcore_memory(self) -> Tuple[bool, List[str]]:
        """Check for remaining AgentCore Memory resources matching this sample's agent."""
        try:
            control = self.session.client('bedrock-agentcore-control')
            resp = control.list_memories()
            memories = resp.get('memories', resp.get('items', []))
            sample_memories = [
                mem.get('id', '')
                for mem in memories
                if AGENT_NAME in mem.get('id', '')
            ]

            if sample_memories:
                self.print_status(f"Found {len(sample_memories)} memory resource(s) for this sample", False)
                for mem in sample_memories:
                    print(f"   - {mem}")
                return False, sample_memories
            else:
                self.print_status("No AgentCore Memory resources for this sample found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking AgentCore memory: {e}")
            return False, [f"Error: {e}"]

    def check_cognito_resources(self) -> Tuple[bool, List[str]]:
        """Check for Cognito user pools tagged for this sample."""
        try:
            cognito = self.session.client('cognito-idp')
            account_id = self.account_id
            pools = cognito.list_user_pools(MaxResults=50).get('UserPools', [])
            tagged = []
            for p in pools:
                pool_id = p['Id']
                arn = f"arn:aws:cognito-idp:us-east-1:{account_id}:userpool/{pool_id}"
                try:
                    tags = cognito.list_tags_for_resource(ResourceArn=arn).get('Tags', {})
                except ClientError:
                    tags = {}
                if tags.get(SAMPLE_TAG_KEY) == SAMPLE_TAG_VALUE:
                    tagged.append(f"{p['Name']} ({pool_id})")

            if tagged:
                self.print_status(f"Found {len(tagged)} tagged Cognito pool(s)", False)
                for pool in tagged:
                    print(f"   - {pool}")
                return False, tagged
            else:
                self.print_status("No tagged Cognito User Pools for this sample found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking Cognito: {e}")
            return False, [f"Error: {e}"]
    
    def check_ecr_repositories(self) -> Tuple[bool, List[str]]:
        """Check for ECR repositories tied to this sample's agent."""
        try:
            ecr = self.session.client('ecr')
            repos = ecr.describe_repositories()
            sample_repos = [
                r['repositoryName']
                for r in repos['repositories']
                if AGENT_NAME in r['repositoryName']
            ]

            if sample_repos:
                self.print_status(f"Found {len(sample_repos)} ECR repo(s) for this sample", False)
                for repo in sample_repos:
                    print(f"   - {repo}")
                return False, sample_repos
            else:
                self.print_status("No ECR repositories for this sample found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking ECR: {e}")
            return False, [f"Error: {e}"]
    
    def check_codebuild_projects(self) -> Tuple[bool, List[str]]:
        """Check for CodeBuild projects tied to this sample's agent."""
        try:
            codebuild = self.session.client('codebuild')
            projects = codebuild.list_projects()
            sample_projects = [p for p in projects['projects'] if AGENT_NAME in p]

            if sample_projects:
                self.print_status(f"Found {len(sample_projects)} CodeBuild project(s) for this sample", False)
                for project in sample_projects:
                    print(f"   - {project}")
                return False, sample_projects
            else:
                self.print_status("No CodeBuild projects for this sample found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking CodeBuild: {e}")
            return False, [f"Error: {e}"]
    
    def check_cloudwatch_logs(self) -> Tuple[bool, List[str]]:
        """Check for CloudWatch log groups tied to this sample's agent."""
        try:
            logs = self.session.client('logs')
            log_groups = logs.describe_log_groups()
            sample_logs = [
                lg['logGroupName']
                for lg in log_groups['logGroups']
                if AGENT_NAME in lg['logGroupName']
            ]

            if sample_logs:
                self.print_status(f"Found {len(sample_logs)} log group(s) for this sample", False)
                for lg in sample_logs:
                    print(f"   - {lg}")
                return False, sample_logs
            else:
                self.print_status("No log groups for this sample found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking CloudWatch: {e}")
            return False, [f"Error: {e}"]
    
    def check_iam_roles(self) -> Tuple[bool, List[str]]:
        """Check for IAM roles created by or for this sample."""
        try:
            iam = self.session.client('iam')
            # (a) Roles we created at our IAM path
            path_roles = iam.list_roles(PathPrefix=IAM_PATH).get('Roles', [])
            # (b) Toolkit-auto-created roles tied to this sample's agent
            all_roles = iam.list_roles().get('Roles', [])
            toolkit_roles = [r for r in all_roles if AGENT_NAME in r['RoleName']]

            found = {r['RoleName'] for r in path_roles} | {r['RoleName'] for r in toolkit_roles}
            if found:
                self.print_status(f"Found {len(found)} IAM role(s) for this sample", False)
                for role in sorted(found):
                    print(f"   - {role}")
                return False, list(found)
            else:
                self.print_status("No IAM roles for this sample found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking IAM: {e}")
            return False, [f"Error: {e}"]
    
    def check_iam_policies(self) -> Tuple[bool, List[str]]:
        """Check for custom IAM policies tied to this sample."""
        try:
            iam = self.session.client('iam')
            policies = iam.list_policies(Scope='Local').get('Policies', [])
            sample_policies = [
                p['PolicyName']
                for p in policies
                if AGENT_NAME in p['PolicyName'] or RESOURCE_PREFIX in p['PolicyName']
            ]

            if sample_policies:
                self.print_status(f"Found {len(sample_policies)} IAM policy(ies) for this sample", False)
                for policy in sample_policies:
                    print(f"   - {policy}")
                return False, sample_policies
            else:
                self.print_status("No IAM policies for this sample found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking IAM policies: {e}")
            return False, [f"Error: {e}"]
    
    def check_s3_buckets(self) -> Tuple[bool, List[str]]:
        """Check for S3 buckets tagged for this sample (skipping shared toolkit bucket)."""
        try:
            s3 = self.session.client('s3')
            buckets = s3.list_buckets().get('Buckets', [])
            tagged = []
            for b in buckets:
                name = b['Name']
                if name.startswith(SKIP_S3_BUCKET_PREFIX):
                    continue  # shared toolkit bucket — by design
                try:
                    tagging = s3.get_bucket_tagging(Bucket=name).get('TagSet', [])
                except ClientError:
                    continue
                tag_map = {t['Key']: t['Value'] for t in tagging}
                if tag_map.get(SAMPLE_TAG_KEY) == SAMPLE_TAG_VALUE:
                    tagged.append(name)

            if tagged:
                self.print_status(f"Found {len(tagged)} tagged S3 bucket(s) for this sample", False)
                for bucket in tagged:
                    print(f"   - {bucket}")
                return False, tagged
            else:
                self.print_status("No tagged S3 buckets for this sample found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking S3: {e}")
            return False, [f"Error: {e}"]
    
    def check_knowledge_bases(self) -> Tuple[bool, List[str]]:
        """Knowledge Bases are not created by this sample; this check is a no-op safety net."""
        # This sample does not create Knowledge Bases, but the original cleanup
        # script looked for them. Keep a no-op stub so accidental KB creation
        # by a user modifying the sample doesn't go silent.
        self.print_status("Skipped (this sample does not create Knowledge Bases)")
        return True, []
    
    def check_lambda_functions(self) -> Tuple[bool, List[str]]:
        """Check for this sample's Lambda function by exact name."""
        try:
            lambda_client = self.session.client('lambda')
            functions = lambda_client.list_functions().get('Functions', [])
            expected_name = f"{RESOURCE_PREFIX}-hr-tools-mcp"
            sample_functions = [
                f['FunctionName']
                for f in functions
                if f['FunctionName'] == expected_name
            ]

            if sample_functions:
                self.print_status(f"Found {len(sample_functions)} Lambda function(s) for this sample", False)
                for func in sample_functions:
                    print(f"   - {func}")
                return False, sample_functions
            else:
                self.print_status(f"No Lambda function named '{expected_name}' found")
                return True, []
        except Exception as e:
            self.print_warning(f"Error checking Lambda: {e}")
            return False, [f"Error: {e}"]
    
    def check_local_files(self) -> Tuple[bool, List[str]]:
        """Check for remaining local configuration files."""
        config_files = ['.env', '.bedrock_agentcore.yaml']
        remaining_files = [f for f in config_files if os.path.exists(f)]
        
        if remaining_files:
            self.print_status(f"Found {len(remaining_files)} local config files", False)
            for config in remaining_files:
                print(f"   - {config}")
            return False, remaining_files
        else:
            self.print_status("No local configuration files found")
            return True, []
    
    def run_verification(self) -> bool:
        """Run complete verification and return True if all clean."""
        self.print_section(f"🔍 Cleanup Verification for {SAMPLE_ID}")
        
        checks = [
            ("🏃 AgentCore Runtime Registrations", self.check_agent_runtimes),
            ("🌐 AgentCore Gateways", self.check_agentcore_gateways),
            ("🧠 AgentCore Memory", self.check_agentcore_memory),
            ("📋 Cognito User Pools", self.check_cognito_resources),
            ("📦 ECR Repositories", self.check_ecr_repositories),
            ("🏗️  CodeBuild Projects", self.check_codebuild_projects),
            ("📊 CloudWatch Log Groups", self.check_cloudwatch_logs),
            ("🔐 IAM Roles", self.check_iam_roles),
            ("📋 IAM Policies", self.check_iam_policies),
            ("🪣 S3 Buckets", self.check_s3_buckets),
            ("📚 Knowledge Bases", self.check_knowledge_bases),
            ("⚡ Lambda Functions", self.check_lambda_functions),
            ("📁 Local Configuration", self.check_local_files),
        ]
        
        all_clean = True
        issues = []
        
        for check_name, check_func in checks:
            print(f"\n{check_name}...")
            try:
                is_clean, problems = check_func()
                if not is_clean:
                    all_clean = False
                    issues.extend(problems)
            except Exception as e:
                self.print_warning(f"Error during {check_name}: {e}")
                all_clean = False
                issues.append(f"{check_name}: {e}")
        
        # Summary
        self.print_section("📊 Cleanup Verification Summary")
        
        if all_clean:
            self.print_status("🎉 All resources for this sample have been cleaned up!")
            self.print_info("(Shared toolkit resources — S3 build bucket, service-linked role — are intentionally left in place.)")
            self.print_info("You can now safely run a fresh deployment:")
            print("   make deploy  (or ./scripts/deploy.sh)")
        else:
            self.print_status(f"❌ Found {len(issues)} remaining issues", False)
            self.print_info("Manual cleanup may be required for remaining resources")
            self.print_info("You can run the complete cleanup script again:")
            print("   ./scripts/complete_cleanup.sh")
        
        return all_clean

def main():
    """Main function."""
    verifier = CleanupVerifier()
    success = verifier.run_verification()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()