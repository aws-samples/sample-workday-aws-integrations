# DevCon Hackathon — Sample Agentflow

## What's Included

`devcon-sample-agentflow.json` — A pre-configured agentflow using Claude Sonnet 4.6 on Amazon Bedrock with image uploads and a Calculator tool enabled.

## Prerequisites

- Flowise running locally (`pnpm dev`)
- AWS credentials configured with Bedrock access (access key + secret key, or AWS profile)

## Setup

1. Start Flowise on your machine:
   ```bash
   cd Flowise
   pnpm install
   pnpm build
   pnpm dev
   ```
   UI available at http://localhost:8080

2. Configure AWS credentials:
   - Go to **Credentials** → **Add New** → **AWS security credentials**
   - Enter your Access Key ID and Secret Access Key (And AWS Session Key if you are using temporary credentials such as IAM Roles)

## Importing the Sample Agentflow

1. Go to **Agent Flows** (left sidebar) → click the **gear icon** (⚙️) in the top right → click **Load Agentflow**
2. Select `devcon-sample-agentflow.json` from your file system
3. The flow will load on the canvas (Start → Agent → Direct Reply)
4. Configure the AWS credential on the Agent node:
   - Open the **Agent** node (double-click)
   - Expand **AWS Bedrock Parameters**
   - Under **Connect Credential**, select the AWS credential you created in the Setup section
   - Close the config
5. Click the **Save** button (floppy disk icon) or press Ctrl+S
6. Open the chat panel (💬 icon in the top right) to start interacting

## What You Can Do

**Text chat:**
> What is the capital of France?

**Math with Calculator tool:**
> What is 1847 multiplied by 293?

The model will invoke the Calculator tool and return the computed result (541,171).

**Image upload (multimodal):**
1. Click the attachment icon in the chat input
2. Upload a photo (PNG/JPG)
3. Ask: "Describe what you see in this image"

## Configuration

The sample uses:
- **Model:** Claude Sonnet 4.6 (`anthropic.claude-sonnet-4-6`)
- **Region:** us-east-1
- **Image uploads:** enabled
- **Tool:** Calculator (built-in)
- **Max tokens:** 1024

To change the model or region, open the Agent node → expand **AWS Bedrock Parameters** → modify as needed.

## Adding Custom Tools

The imported agentflow comes pre-configured with the built-in Calculator tool. **To add a custom tool, you must build a new agentflow from scratch** rather than editing this imported one.

Custom tools are referenced in the agentflow JSON by their database ID (a UUID generated when the tool is created). That ID is unique to your local Flowise instance — we can't include it in a shared JSON file. Imported agentflows also don't expose the tool selector UI.

**To use a custom tool:**

1. Go to **Tools** → **Add New** → define your tool (name, description, input schema, JavaScript function) → **Save**
2. Go to **Agent Flows** → **Add New** → drag a Start, Agent, and Direct Reply node onto the canvas and connect them
3. Open the Agent node → set the model to **AWS Bedrock** → under **Tools**, select **Custom Tool** → choose the tool you just created
4. Save the flow

**Note:** Custom tool execution requires the `E2B_APIKEY` environment variable to be set in `packages/server/.env`. Get a free key at [e2b.dev](https://e2b.dev).

### Alternative: Modify the JSON Before Import

If you'd rather start from this sample agentflow than build one from scratch:

1. Create your custom tool via the UI (Tools → Add New) and save it
2. Find the tool's UUID:
   - Open the tool — the URL will look like `/tools/<uuid>`
   - Or query `GET http://localhost:3000/api/v1/tools` and find the `id` field
3. Open `devcon-sample-agentflow.json` in a text editor and replace the `agentTools` block:
   ```json
   "agentTools": [
       {
           "agentSelectedTool": "customTool",
           "agentSelectedToolConfig": {
               "selectedTool": "<paste-your-tool-uuid-here>"
           },
           "agentSelectedToolRequiresHumanInput": false
       }
   ]
   ```
4. Import the modified JSON (Agent Flows → gear icon → Load Agentflow)

## Troubleshooting

- **No response / timeout:** Verify your AWS credentials have `bedrock:InvokeModel` permissions in the selected region.
- **"The provided model identifier is invalid":** The selected model may not be available in your chosen region. Switch to `us-east-1` or `us-west-2` for broadest model availability.
- **Blank model dropdown:** Ensure Flowise was built after pulling the latest code (`pnpm build`).
