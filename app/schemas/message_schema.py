from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    sender_id: str
    content: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sender_id": "68805dc7bf5491c521b0d31a",
                "content": "hello",
            }
        }
    )


class MessageUpdate(BaseModel):
    content: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"content": "good morning"}}
    )
