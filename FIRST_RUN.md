# First-Run Setup

When you first launch Ayeneh, the Setup Wizard guides you through configuration.

## Steps

### 1. Select Product Profile
Choose how Ayeneh behaves:
- **Ayeneh**: Cognitive Companion for self-observation
- **Career Mentor**: Professional development guidance
- **Business Advisor**: Strategic business analysis

### 2. Configure LLM Provider
Select your LLM provider (OpenAI, Anthropic, Gemini, or LiteLLM) and enter your API key. The system validates the key immediately.

### 3. Configure Embeddings
The embedding provider is typically the same as your LLM provider. Configure the model for text embeddings.

### 4. Configure Storage
Verify your PostgreSQL database connection. The system runs migrations automatically.

### 5. Run Diagnostics
Complete a full health check of all services before starting.

## Resumability

The wizard saves progress at each step. If you close the browser, revisit `/wizard` to continue where you left off.

## Reconfiguration

Visit Settings at any time to update:
- LLM provider and model
- API keys
- Temperature and token limits
- Fallback model chain
