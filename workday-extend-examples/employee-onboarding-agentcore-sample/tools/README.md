# HR Onboarding Tools (Lambda backend — not part of the agent container)

This directory contains the MCP tool implementations that run inside the
Lambda function (`bedrock-employee-onboarding-hr-tools-mcp`). The agent
does **not** import from this directory — it discovers these tools at runtime
via MCP from the AgentCore Gateway. `deploy.sh` packages this directory into
a zip and deploys it as a Lambda function.

## Tools Included

### 1. Employee Directory Tool
- **Purpose**: Look up employee information for manager assignment and team introductions
- **Capabilities**: Search by name, department, or role
- **Returns**: Employee details, manager info, mentor availability

### 2. IT Asset Management Tool  
- **Purpose**: Check equipment availability and create provisioning requests
- **Capabilities**: Role-based equipment recommendations, availability checking
- **Returns**: Equipment availability, delivery times, provisioning requests

## Implementation

These tools use mock data to simulate realistic HR and IT systems without requiring external databases or services.

## Usage

The tools are automatically discovered and registered by the AgentCore Gateway through the MCP protocol. The Strands agent calls these tools during the onboarding process to:

1. Find appropriate managers and mentors
2. Determine role-specific equipment needs
3. Check availability and delivery times
4. Create personalized onboarding experiences

## Mock Data

All data is stored in `mock_data.py` and includes:
- Employee directory with realistic roles and departments
- IT equipment inventory with availability and delivery times
- Role-based equipment recommendations