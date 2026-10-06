.pragma library
var presets = [
    {label:"Ollama",value:"ollama",protocol:"ollama",url:"http://127.0.0.1:11434"},
    {label:"LM Studio",value:"lmstudio",protocol:"openai",url:"http://127.0.0.1:1234/v1"},
    {label:"llama.cpp / GGUF",value:"llamacpp",protocol:"openai",url:"http://127.0.0.1:8080/v1"},
    {label:"vLLM / SGLang",value:"vllm",protocol:"openai",url:"http://127.0.0.1:8000/v1"},
    {label:"LocalAI",value:"localai",protocol:"openai",url:"http://127.0.0.1:8080/v1"},
    {label:"Jan",value:"jan",protocol:"openai",url:"http://127.0.0.1:1337/v1"},
    {label:"KoboldCpp",value:"koboldcpp",protocol:"openai",url:"http://127.0.0.1:5001/v1"},
    {label:"text-generation-webui",value:"textgen",protocol:"openai",url:"http://127.0.0.1:5000/v1"},
    {label:"OpenRouter",value:"openrouter",protocol:"openai",url:"https://openrouter.ai/api/v1"},
    {label:"Hugging Face Inference",value:"huggingface",protocol:"openai",url:"https://router.huggingface.co/v1"},
    {label:"Свой совместимый сервер",value:"custom",protocol:"openai",url:"http://127.0.0.1:8080/v1"}
]
function preset(id) { return presets.find(p => p.value === id) || presets[0] }
