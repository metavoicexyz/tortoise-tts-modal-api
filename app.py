import os

import modal
from fastapi import Request
from fastapi.responses import Response

from model import TortoiseModal, stub

###### MODAL CPU API Key Logic.

supabase_image = modal.Image.debian_slim().pip_install("supabase")


@stub.webhook(
    method="POST",
    image=supabase_image,
    secret=modal.Secret.from_name("supabase-tortoise-secrets"),
)
def app(req: Request):
    """
    POST endpoint for running Tortoise. Checks whether the user exists,
    and adds usage time to the user's account.
    """
    import asyncio
    import time

    from supabase import Client, create_client

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    body = asyncio.run(req.json())
    text = body["text"]
    voices = body["voices"]
    api_key = body["api_key"]
    target_file_web_path = body.get("target_file", None)

    data = supabase.table("users").select("*").eq("api_key", api_key).execute().data

    if len(data) == 1:
        # user is registered.

        start = time.time()
        wav = TortoiseModal().run_tts.call(text, voices, target_file_web_path)
        end = time.time()

        # Update the user's usage.
        fresh_data_usage_dollar = (
            supabase.table("users")
            .select("*")
            .eq("api_key", api_key)
            .execute()
            .data[0]["usage_dollar"]
        )
        supabase.table("users").update(
            {"usage_dollar": fresh_data_usage_dollar + 0.0005833 * (end - start)}
        ).eq("api_key", api_key).execute()

        return Response(content=wav.getvalue(), media_type="audio/wav")
    else:
        # return a 401
        return Response(status_code=401)


if __name__ == "__main__":
    stub.serve()