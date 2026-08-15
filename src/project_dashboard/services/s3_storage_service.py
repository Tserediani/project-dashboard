class S3StorageService:
    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        # TODO
        raise NotImplementedError

    async def generate_presigned_url(self, key: str, expires_in: int) -> str:
        # TODO
        print(f"Generated presigned url: {key} - {expires_in}")
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        # TODO
        raise NotImplementedError
