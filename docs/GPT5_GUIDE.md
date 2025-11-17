# GPT-5 API Support Guide

## Overview

LitRelevanceAI now supports OpenAI's GPT-5 and o1 series models through their new Responses API. The implementation provides automatic detection and seamless integration while maintaining backward compatibility with GPT-4, GPT-3.5, and other models.

## Key Differences Between GPT-4 and GPT-5 APIs

### API Methods

- **GPT-4 and earlier**: Uses `chat.completions.create()`
- **GPT-5 and o1 series**: Uses `responses.create()`

### Parameter Changes

#### Removed Parameters (GPT-5)
- `temperature` - No longer supported
- `top_p` - No longer supported
- `frequency_penalty` - No longer supported
- `presence_penalty` - No longer supported
- `max_tokens` - Replaced by structured control

#### New Parameters (GPT-5)

1. **verbosity**: Controls output length and detail
   - `low` - Concise responses (~560 tokens)
   - `medium` - Balanced detail (~850 tokens) - **default**
   - `high` - Comprehensive responses (~1300+ tokens)

2. **reasoning_effort**: Controls computational effort for reasoning
   - `low` - Faster responses with basic reasoning
   - `medium` - Balanced speed and depth - **default**
   - `high` - Maximum reasoning capability

3. **store**: Boolean flag for stateful conversation management
   - `true` - Enables conversation history storage - **default**
   - `false` - Stateless requests

### Message Format Changes

**GPT-4 format**:
```python
messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello"}
]
```

**GPT-5 format**:
```python
input = [
    {
        "role": "developer",  # "system" → "developer"
        "content": [{"type": "input_text", "text": "You are a helpful assistant"}]
    },
    {
        "role": "user",
        "content": [{"type": "input_text", "text": "Hello"}]
    }
]
```

### Response Format Changes

**GPT-4 response**:
```python
content = response["choices"][0]["message"]["content"]
```

**GPT-5 response**:
```python
content = response.output_text
# or
content = response.output[1].content[0].text
```

## Usage in LitRelevanceAI

### Automatic Detection

The `AIClient` class automatically detects GPT-5 and o1 models and uses the appropriate API:

```python
from litrx.ai_client import AIClient

# Automatically uses Responses API for GPT-5
config = {
    "AI_SERVICE": "openai",
    "MODEL_NAME": "gpt-5",
    "OPENAI_API_KEY": "your-api-key"
}
client = AIClient(config)

# Use the same interface as before
response = client.request(
    messages=[{"role": "user", "content": "Analyze this paper..."}]
)
content = response["choices"][0]["message"]["content"]
```

### Configuration

#### Environment Variables (.env)

```bash
OPENAI_API_KEY=sk-...
VERBOSITY=medium  # Optional: low, medium, high
REASONING_EFFORT=medium  # Optional: low, medium, high
```

#### YAML Configuration (configs/config.yaml)

```yaml
AI_SERVICE: openai
MODEL_NAME: gpt-5
OPENAI_API_KEY: "sk-..."
VERBOSITY: medium
REASONING_EFFORT: medium
```

#### Python Configuration

```python
config = {
    "AI_SERVICE": "openai",
    "MODEL_NAME": "gpt-5",
    "OPENAI_API_KEY": "sk-...",
    "VERBOSITY": "high",  # Request detailed responses
    "REASONING_EFFORT": "high"  # Request deep reasoning
}
```

## Model-Specific Behavior

### GPT-5 Models

- Model names containing "gpt-5" (e.g., `gpt-5`, `gpt-5-turbo`)
- Supports: `verbosity`, `reasoning`, `tools`, `store`
- Automatically converts old-style parameters

### o1 Series Models

- Model names starting with "o1" (e.g., `o1`, `o1-mini`, `o1-preview`)
- **Special restrictions**:
  - Does NOT support `temperature`, `top_p`
  - Does NOT support `reasoning` parameter
  - Uses `max_completion_tokens` instead of `max_tokens`
  - Does NOT support streaming
  - Does NOT support system messages (only `user` and `developer`)

### GPT-4 and Earlier Models

- Model names: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`, etc.
- Uses traditional `chat.completions` API via LiteLLM
- Supports: `temperature`, `top_p`, `max_tokens`, etc.

## Examples

### Basic Usage with GPT-5

```python
from litrx.csv_analyzer import LiteratureAnalyzer

config = {
    "AI_SERVICE": "openai",
    "MODEL_NAME": "gpt-5",
    "OPENAI_API_KEY": "sk-...",
    "VERBOSITY": "medium",
    "REASONING_EFFORT": "medium"
}

analyzer = LiteratureAnalyzer(
    config=config,
    research_topic="Machine Learning in Healthcare"
)

# Works exactly the same as with GPT-4
results = analyzer.analyze_papers(df)
```

### Using o1 Models

```python
config = {
    "AI_SERVICE": "openai",
    "MODEL_NAME": "o1-preview",
    "OPENAI_API_KEY": "sk-...",
    "VERBOSITY": "medium"
    # Note: No REASONING_EFFORT for o1 models
}

analyzer = LiteratureAnalyzer(config=config, research_topic="...")
results = analyzer.analyze_papers(df)
```

### Mixing Models

You can use different models for different tasks:

```python
# Use GPT-5 for detailed analysis
gpt5_config = {
    "MODEL_NAME": "gpt-5",
    "VERBOSITY": "high",
    "REASONING_EFFORT": "high"
}
detailed_client = AIClient(gpt5_config)

# Use GPT-4o for quick screening
gpt4_config = {
    "MODEL_NAME": "gpt-4o",
    "TEMPERATURE": 0.3
}
quick_client = AIClient(gpt4_config)
```

## Advanced Features (GPT-5 Only)

### Custom Tools

GPT-5 supports custom tool integration (not currently exposed in LitRelevanceAI):

```python
# Future feature - example of what will be possible
response = client.request(
    messages=[...],
    tools=[{
        "type": "custom",
        "name": "database_query",
        "description": "Query research database"
    }]
)
```

### Web Search Integration

```python
# Future feature
response = client.request(
    messages=[...],
    tools=[{"type": "web_search_preview"}]
)
```

### MCP Server Integration

```python
# Future feature
response = client.request(
    messages=[...],
    tools=[{
        "type": "mcp",
        "server_url": "https://...",
        "server_label": "research_db"
    }]
)
```

## Troubleshooting

### Error: "需要安装 openai 包以使用 GPT-5 或 o1 模型"

Install the OpenAI SDK:
```bash
pip install openai
```

### Error: Parameter not supported for this model

Check if you're using the right parameters for your model:
- GPT-5: Remove `temperature`, `top_p`, etc.
- o1 series: Remove `reasoning_effort`, use only `verbosity`
- GPT-4: Remove `verbosity`, use `temperature` instead

### Unexpected Response Format

The `AIClient` automatically converts GPT-5 responses to the old format for compatibility. If you need the raw response:

```python
response = client.request(messages=[...])
raw_gpt5_response = response.get("_raw_response")
```

## Performance Considerations

### Response Time

- **GPT-5 with high reasoning_effort**: Slower but more accurate
- **GPT-5 with low reasoning_effort**: Faster, suitable for simple tasks
- **o1 models**: Optimized for specific reasoning tasks
- **GPT-4o**: Balanced performance for most tasks

### Token Usage

- **Verbosity setting** significantly affects token consumption:
  - `low`: ~560 tokens per response
  - `medium`: ~850 tokens per response
  - `high`: ~1300+ tokens per response

### Cost Optimization

1. Use `verbosity: low` for screening tasks
2. Use `verbosity: high` only for final analysis
3. Consider GPT-4o for bulk processing
4. Use GPT-5 for complex reasoning tasks only

## Migration Guide

### Updating Existing Code

No changes needed! The `AIClient` automatically handles:
- Parameter conversion
- Response format normalization
- Model-specific restrictions

### Recommended Migration Path

1. **Test with GPT-4o first**: Ensure your prompts work well
2. **Try GPT-5 with medium settings**: Compare quality and cost
3. **Optimize settings**: Adjust `verbosity` and `reasoning_effort`
4. **Monitor costs**: GPT-5 may be more expensive

### Example Migration

**Before (GPT-4)**:
```python
config = {
    "MODEL_NAME": "gpt-4o",
    "TEMPERATURE": 0.3,
    "MAX_TOKENS": 2048
}
```

**After (GPT-5)**:
```python
config = {
    "MODEL_NAME": "gpt-5",
    "VERBOSITY": "medium",
    "REASONING_EFFORT": "medium"
}
```

## References

- [OpenAI GPT-5 Documentation](https://platform.openai.com/docs/models/gpt-5)
- [GPT-5 Cookbook](https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools)
- [OpenAI Python SDK](https://github.com/openai/openai-python)

## Version Compatibility

- **LitRelevanceAI**: v0.1.0+
- **OpenAI Python SDK**: v1.0.0+
- **LiteLLM**: v1.0.0+ (for non-GPT-5 models)

## Future Enhancements

Planned features for GPT-5 integration:
- [ ] Custom tool support for database queries
- [ ] Web search integration for real-time data
- [ ] MCP server support for external services
- [ ] Streaming responses for long analyses
- [ ] Reasoning trace visualization
- [ ] Cost tracking and optimization tools
