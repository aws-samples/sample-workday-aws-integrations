Amazon Web Services and Workday - Better Together

Hello Workday developers! My name is Anthony McClure and I am a Solutions Architect with the AWS business applications team. As a part of this team I have the disctict pleasure of getting to work with amazing partners like Workday. Along with other team members on the AWS Workday account team we have been co-building solutions to assist Workday customers to take advantage of Workday Orchestrations and AWS services. In this post I will discuss examples of this integration using Workday Extend functionality.
What is Workday Extend?

Workday Extend is a powerful platform that allows organizations to build custom applications and integrations that seamlessly connect with Workday’s core functionality. It provides the flexibility to extend Workday’s capabilities while maintaining the security, compliance, and user experience standards that Workday is known for.
How Workday Extend Works

Workday Extend operates on several key principles:

    External Endpoints: Connect to external services and APIs through secure, configurable endpoints

    Custom Objects: Create custom data structures that integrate with Workday’s existing data model

    Business Processes: Build workflows that can trigger external actions or consume external data

    Orchestrations: Coordinate complex multi-step processes that span both Workday and external systems

    Security: Leverage Workday’s robust security model with OAuth 2.0 and other enterprise-grade authentication mechanisms

AWS Integration with Workday Extend

The AWS account team for Workday has been developing practical examples that demonstrate how Workday Extend can leverage AWS services to create powerful, scalable solutions. These integrations showcase the potential for organizations to extend their Workday investments with cloud-native capabilities.
Translation Service Example

One compelling example is an AWS Lambda-based translation service that integrates with Workday Extend. This solution demonstrates:

Key Features:

    Real-time text translation using AWS Translate

    Serverless architecture for cost-effective scaling

    Simple JSON API interface for easy integration

    Support for multiple language pairs with auto-detection

Technical Implementation:

    Built using AWS SAM (Serverless Application Model) for easy deployment

    Python-based Lambda function with minimal dependencies

    Configurable source and target languages

    Error handling and logging for production readiness

Integration Points:

    External endpoint configuration in Workday Extend

    JSON request/response format compatible with Workday business processes

    Can be triggered from custom applications or orchestrations

Calculation Function Example

A colleague of mine, Alicia Bain, has also developed a Lambda-based calculation function that showcases another common use case - performing complex calculations that might be resource-intensive or require specialized libraries not available within Workday’s native environment. I will attach the source code for both solutions to this post.
Working with Orchestrations

One of the most powerful aspects of these AWS integrations is how they work with Workday Orchestrations:

Sequential Processing: Orchestrations can call multiple AWS services in sequence, passing data between steps and maintaining state throughout the process.

Conditional Logic: Based on responses from AWS services, orchestrations can branch to different paths, enabling sophisticated business logic.

Error Handling: Orchestrations provide robust error handling capabilities, allowing for retry logic, fallback procedures, and proper error reporting.

Data Transformation: Results from AWS services can be transformed and mapped back into Workday objects, ensuring seamless data flow.
Getting Started

For organizations interested in implementing similar solutions, we’ve created comprehensive documentation to guide you through the process:
Deployment Guide

The WORKDAY_DEPLOYMENT_GUIDE.md file in our repository provides detailed, step-by-step instructions for:

    Setting up the AWS CLI and SAM CLI

    Configuring your AWS environment

    Deploying Lambda functions using infrastructure as code

    Configuring Workday Extend external endpoints

    Testing and troubleshooting your integration

Key Steps Overview

    AWS Environment Setup: Install necessary tools (AWS CLI, SAM CLI, Docker)

    Deploy AWS Resources: Use SAM to deploy Lambda functions and associated resources

    Configure Workday Extend: Set up external endpoints pointing to your AWS resources

    Create Business Processes: Build Workday processes that consume your AWS services

    Test and Monitor: Validate functionality and set up monitoring/logging

Benefits of This Approach

Scalability: AWS services automatically scale based on demand, ensuring your Workday extensions can handle varying workloads.

Cost Effectiveness: Serverless architecture means you only pay for what you use, making it economical for both high and low-volume scenarios.

Reliability: AWS’s global infrastructure provides high availability and disaster recovery capabilities.

Security: Integration leverages both Workday’s and AWS’s enterprise-grade security features.

Maintainability: Infrastructure as code approaches make deployments repeatable and version-controlled.
Real-World Applications

These patterns can be applied to numerous business scenarios:

    Document Processing: OCR, document classification, and content extraction

    Data Analytics: Complex calculations, machine learning predictions, and data analysis

    Integration Services: Connecting to third-party APIs, data transformation, and protocol translation

    Notification Services: SMS, email, and push notifications through AWS SNS/SES

    File Processing: Image resizing, format conversion, and batch processing

Next Steps

The examples we’ve shared represent just the beginning of what’s possible when combining Workday Extend with AWS services. We encourage the community to:

    Explore the sample code and deployment guides

    Adapt these patterns to your specific use cases

    Share your own implementations and learnings

    Contribute improvements and additional examples

The intersection of Workday Extend and AWS services opens up tremendous possibilities for organizations looking to maximize their Workday investment while leveraging best-in-class cloud services. These practical examples provide a foundation for building sophisticated, scalable solutions that enhance your Workday environment.