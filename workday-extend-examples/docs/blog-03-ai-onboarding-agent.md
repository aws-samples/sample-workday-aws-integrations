# Building an AI Employee Onboarding Agent with Workday and Amazon Bedrock AgentCore

*By Anthony McClure, Alicia Bane, Fritz Lam, and Gene Krevets*

## Introduction

[Part 1](blog-01-getting-started-with-lambda.md) and [Part 2](blog-02-real-time-translation.md) of this series demonstrated how to connect Workday Extend to AWS services through a familiar pattern: Workday Orchestration calls Lambda, Lambda calls an AWS service, results flow back. That pattern works for deterministic, single-step tasks — calculate a sum, translate a paragraph, validate an address.

Employee onboarding is different. It requires reasoning across multiple data sources (HR systems, IT inventory, knowledge bases), generating a personalized package of information, and adapting its output based on what it discovers. A new software engineer needs different equipment, access permissions, and first-week schedules than a new sales representative. The logic is not a fixed pipeline but a dynamic decision process.

This is the use case for agentic AI: a model that can plan, discover available tools, call them based on the situation, and synthesize results into a coherent output. Amazon Bedrock AgentCore provides the runtime infrastructure to deploy these agents at enterprise scale, with built-in authentication, streaming, tool orchestration, and observability.

This post walks through deploying an AI-powered employee onboarding assistant that uses Claude Haiku 4.5 on Amazon Bedrock, discovers HR and IT tools dynamically through the Model Context Protocol (MCP), authenticates via OAuth2, and streams structured responses back to the caller. The agent produces a complete onboarding package (IT provisioning, welcome message, daily schedule, 30-day goals) grounded entirely in data retrieved through tool calls — it fabricates nothing.

## Why Agentic AI for Onboarding?

Traditional onboarding automation follows rigid scripts: send welcome email on Day -7, create accounts on Day -3, schedule orientation on Day 1. These scripts break when the situation varies:

- A remote employee in Berlin needs a European equipment shipping address and German-language materials
- An engineer joining the ML platform team needs GPU-enabled workstation provisioning and specific Sagemaker access
- A contractor starting mid-sprint needs abbreviated onboarding focused on immediate tool access

An AI agent handles variation by design. Instead of encoding every branch in an orchestration flowchart, the agent reasons about what information it needs, retrieves it through tools, and generates a tailored output. The Workday system provides the trigger (new hire event); the agent handles the intelligence.

## Architecture Overview

```
User/Orchestrator → AgentCore Runtime → Claude Haiku 4.5 → MCP Gateway → Lambda (HR Tools)
                  ←─── streaming SSE ────────────────────────────────────────────────────
```

Five components work together:

1. **Amazon Bedrock AgentCore Runtime** — Hosts the agent as a containerized HTTP endpoint. Handles scaling, authentication, streaming, retries, logging, and metrics. You deploy code; AgentCore handles infrastructure.

2. **Strands Agent SDK** — A Python SDK for building agents with Amazon Bedrock models. Manages conversation history, tool calling, and streaming output. The agent is defined with a system prompt, a model (Claude Haiku 4.5), and access to MCP tools.

3. **AgentCore Gateway (MCP)** — An MCP-compatible proxy that sits between the agent and its tools. Handles tool discovery (the agent asks "what tools do you have?"), request routing, and OAuth2 authentication. Tools are registered at the gateway; the agent discovers them dynamically at runtime.

4. **Lambda (Tool Backend)** — Implements the actual tool logic: employee directory lookups, IT asset inventory checks, policy retrieval. Deployed behind the MCP Gateway. In production, these would connect to Workday APIs, ServiceNow, or your HRIS; in this sample, they return mock data for demonstration.

5. **Amazon Cognito** — Provides OAuth2 client-credentials authentication for both the runtime invocation (client → runtime) and tool access (agent → gateway). Two separate OAuth2 flows ensure that both the calling client and the agent itself are authenticated.

## Key Concepts

Before diving into the code, here are the concepts that differentiate this example from Parts 1 and 2:

**Model Context Protocol (MCP)** — An open standard for agents to discover and call tools over HTTP. Instead of hard-coding tool definitions in your agent, the agent asks the MCP Gateway "what tools do you have?" at startup and receives JSON schemas it can invoke. This means you can add, remove, or update tools without redeploying the agent.

**Server-Sent Events (SSE)** — A protocol for streaming data from server to client over HTTP. The runtime uses SSE to stream the agent's response token-by-token as it generates, enabling real-time display rather than waiting for the full response. The streaming response includes tool call notifications, reasoning traces, and the final structured output.

**ToolTrace** — A custom section appended to every response showing which MCP tools were called, with what arguments, and what they returned. This provides transparency into the agent's decision-making process and is critical for debugging and audit trails.

**Client-credentials OAuth2 flow** — Machine-to-machine authentication. Both the CLI (calling the runtime) and the agent (calling the gateway) use OAuth2 client credentials to obtain access tokens from Cognito. No human login is required.

## Technical Walkthrough

### Prerequisites

- macOS (Monterey+) or Amazon Linux 2023
- Python 3.10+
- AWS CLI configured with credentials (`aws configure`)
- AWS account with Claude Haiku 4.5 model access enabled in `us-east-1` ([enable here](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess))
- `AdministratorAccess` in a sandbox account (see DEPLOYMENT.md for a scoped policy)

### Step 1: Deploy

```bash
git clone https://github.com/aws-samples/sample-workday-aws-integrations.git
cd workday-extend-examples/employee-onboarding-agentcore-sample
make deploy
```

This single command deploys the full stack (~10-15 minutes on first run):
- Builds the Docker container with the Strands agent
- Deploys the AgentCore Runtime
- Creates a Cognito user pool with client credentials
- Configures the MCP Gateway with OAuth2
- Deploys the Lambda function with HR/IT tool implementations
- Registers tools at the gateway

The deployment is idempotent. Run it again after code changes to update the runtime and Lambda without recreating the gateway or Cognito pool.

### Step 2: The Agent (onboarding_app.py)

The core of the system is the Strands agent definition:

```python
from strands import Agent
from strands.models.bedrock import BedrockModel

model = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20250901-v1:0",
    region_name="us-east-1",
    temperature=0.0
)

agent = Agent(
    model=model,
    system_prompt=system_prompt,  # loaded from prompts/onboarding.txt
    tools=mcp_tools,             # discovered dynamically from Gateway
    conversation_manager=SlidingWindowConversationManager()
)
```

Key design decisions:

- **Temperature 0.0** — Deterministic output. The agent calls the same tools and produces consistent results for the same input, critical for HR processes.
- **System prompt requires tool use** — The prompt explicitly instructs the model to call tools before writing each section. It must not fabricate people, hardware, or inventory. This constraint ensures every fact in the onboarding package comes from a verified data source.
- **Dynamic tool discovery** — `mcp_tools` is not a static list. The agent connects to the MCP Gateway at invocation time, authenticates via Cognito, and discovers available tools. Adding a new tool to the gateway makes it instantly available to the agent.

### Step 3: MCP Tool Discovery and Authentication

The agent discovers tools through the Gateway:

```python
async def _ensure_tools(self):
    """Connect to MCP Gateway and discover available tools."""
    token = await self._get_cognito_token()  # OAuth2 client-credentials
    
    mcp_client = MCPClient(
        gateway_url=os.environ["AGENTCORE_MCP_URL"],
        auth_token=token
    )
    
    tools = await mcp_client.list_tools()  # MCP discovery
    return tools
```

The Gateway responds with tool schemas:

```json
{
  "tools": [
    {
      "name": "lookup_employee",
      "description": "Look up employee details by name",
      "inputSchema": {
        "type": "object",
        "properties": {
          "employee_name": {"type": "string"}
        },
        "required": ["employee_name"]
      }
    },
    {
      "name": "check_it_inventory",
      "description": "Check available IT equipment for provisioning",
      "inputSchema": {
        "type": "object",
        "properties": {
          "department": {"type": "string"},
          "role": {"type": "string"}
        }
      }
    }
  ]
}
```

Claude sees these schemas and decides which tools to call based on the user's prompt. If the user says "onboard Jane Doe as software engineer," Claude calls `lookup_employee` with Jane Doe's name, then `check_it_inventory` for engineering equipment.

### Step 4: Streaming Response

The agent streams its response as Server-Sent Events:

```
data: {"text": "[Reasoning: it] Looking up employee details..."}
data: {"text": "[Result: it] Based on the employee directory..."}
data: {"text": "[Reasoning: welcome] Composing welcome message..."}
data: {"text": "[Result: welcome] Welcome to the team, Jane!..."}
data: {"text": "[ToolTrace] lookup_employee({name: 'Jane Doe'}) → {...}"}
```

The response is structured into tagged sections:
- **Reasoning** — The agent's thought process (why it's calling a tool, what it plans to generate)
- **Result** — The generated content for each section (IT provisioning, welcome, daily schedule, 30-day plan)
- **ToolTrace** — Audit trail of every tool call with arguments and return values

### Step 5: Test

```bash
# Quick smoke test
make smoke-test

# CLI with formatted output
make cli

# Custom prompt
make cli PROMPT="onboard Jane Doe as software engineer"
```

The CLI authenticates via Cognito, streams the SSE response, and renders it into formatted sections in your terminal.

### Step 6: Clean Up

```bash
make clean
make verify-clean
```

## How It Connects to Workday

In production, this agent integrates with Workday through two paths:

**Path 1: Workday Orchestration triggers the agent.** A Workday Business Process (new hire event) triggers an Orchestration that calls the AgentCore Runtime endpoint via an External Endpoint. The orchestration passes the employee name and role; the agent generates the onboarding package; the orchestration stores results in Workday custom objects.

**Path 2: The agent's tools call Workday APIs.** Instead of mock data, the Lambda tool backends call Workday REST APIs (via Workday Extend external endpoints) to retrieve real employee data, department structures, and equipment allocation. The MCP Gateway handles authentication to each backend.

Both paths can operate simultaneously: Workday triggers the agent, and the agent reads from Workday.

## Architecture Considerations

### Security

- AgentCore Runtime authenticates all callers via Cognito OAuth2 (client-credentials flow)
- The MCP Gateway authenticates the agent separately before granting tool access
- Tools run as Lambda functions with least-privilege IAM roles
- No secrets in code — all credentials flow through environment variables injected at deployment
- The system prompt prevents data fabrication, ensuring the agent only outputs verified tool results

### Cost

- **Bedrock (Claude Haiku 4.5)**: ~$0.25 per 1M input tokens, ~$1.25 per 1M output tokens. A typical onboarding generation (including tool calls) uses ~3K input + 2K output tokens ≈ $0.003 per onboarding.
- **AgentCore Runtime**: Charged per invocation-second while the agent is running
- **Lambda (tool backends)**: Standard Lambda pricing (negligible at onboarding volumes)
- **Cognito**: Free tier covers 50,000 monthly active users

### Observability

- CloudWatch metrics at `/aws/bedrock-agentcore/runtimes/[agent-id]-DEFAULT`
- Every tool call is captured in the ToolTrace output
- Runtime emits human-readable notices for rate limits, retries, and errors
- Session IDs enable end-to-end request tracing

### Scaling

- AgentCore Runtime scales horizontally based on request volume
- Gateway handles concurrent tool calls from multiple agent sessions
- Lambda backends scale independently per function
- No infrastructure management required

## Extending This Example

| Extension | How |
|---|---|
| **Real Workday data** | Replace mock Lambda tools with Workday API calls (employee directory, org chart, equipment allocation) |
| **Additional sections** | Add new sections to the system prompt (benefits enrollment, compliance training, team introductions) |
| **Multi-turn conversation** | Use the session ID for follow-up questions ("What about her parking assignment?") |
| **Different models** | Pass `MODEL=us.anthropic.claude-sonnet-4-5-20250929-v1:0` at deploy for higher-capability reasoning |
| **Custom tools** | Register additional Lambda functions at the MCP Gateway (Slack notifications, calendar booking, badge provisioning) |
| **Non-streaming consumers** | Wrap the runtime with API Gateway + Lambda to buffer SSE into a synchronous JSON response for orchestrators that cannot handle streaming |

## Conclusion and Next Steps

This post demonstrated how to deploy an AI agent that reasons about employee onboarding, dynamically discovers tools via MCP, retrieves data from enterprise backends, and streams structured results — all running on Amazon Bedrock AgentCore with enterprise-grade authentication.

The progression across this three-part series mirrors the evolution of Workday-AWS integrations:

1. **Part 1** — Deterministic compute: Lambda receives input, returns output (sum)
2. **Part 2** — AI services: Lambda calls managed ML models (translation)
3. **Part 3** — Agentic AI: An autonomous agent plans, discovers tools, retrieves data, and generates context-aware output (onboarding)

Each pattern builds on the previous one. The same Workday Extend primitives (External Endpoints, Orchestrations, Custom Objects) connect to increasingly sophisticated AWS capabilities.

**To get started:**

1. Deploy the sample: `make deploy` in the [employee-onboarding-agentcore-sample](https://github.com/aws-samples/sample-workday-aws-integrations/tree/main/workday-extend-examples/employee-onboarding-agentcore-sample) directory.
2. Run `make cli` to see the agent generate a complete onboarding package with tool calls.
3. Read [ARCHITECTURE.md](https://github.com/aws-samples/sample-workday-aws-integrations/blob/main/workday-extend-examples/employee-onboarding-agentcore-sample/ARCHITECTURE.md) for the component-by-component deep dive.
4. Replace mock tools with your real HR backend to see the agent produce live onboarding packages.


---

## Series Navigation

- [Part 1: Getting Started with Workday Extend and AWS Lambda](blog-01-getting-started-with-lambda.md)
- [Part 2: Real-Time Translation in Workday with AWS Translate and Comprehend](blog-02-real-time-translation.md)
- **Part 3: Building an AI Employee Onboarding Agent with Amazon Bedrock AgentCore** (this post)

---

The complete source code, deployment scripts, architecture documentation, and troubleshooting guides are available in the [aws-samples/sample-workday-aws-integrations](https://github.com/aws-samples/sample-workday-aws-integrations/tree/main/workday-extend-examples) repository on GitHub.
