from litellm.integrations.custom_logger import CustomLogger
from litellm.types.utils import Delta, ModelResponseStream, StreamingChoices


class ModelFooterLogger(CustomLogger):
    async def async_post_call_streaming_iterator_hook(
        self, user_api_key_dict, response, request_data
    ):
        model_used = None
        async for chunk in response:
            if getattr(chunk, "model", None):
                model_used = chunk.model
            yield chunk

        if model_used:
            footer_text = f"\n\n---\n*Model: `{model_used}`*"
            yield ModelResponseStream(
                id="footer-chunk",
                model=model_used,
                choices=[
                    StreamingChoices(
                        index=0,
                        delta=Delta(content=footer_text, role="assistant"),
                        finish_reason=None,
                    )
                ],
            )

    async def async_post_call_success_hook(
        self, data, user_api_key_dict, response
    ):
        model_used = getattr(response, "model", None)
        if model_used and hasattr(response, "choices") and response.choices:
            msg = getattr(response.choices[0], "message", None)
            if msg and isinstance(getattr(msg, "content", None), str):
                msg.content += f"\n\n---\n*Model: `{model_used}`*"


proxy_handler_instance = ModelFooterLogger()