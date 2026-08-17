import aioboto3


class S3StorageService:
    def __init__(self, bucket_name: str, region_name: str, session: aioboto3.Session):
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.endpoint_url = f"https://s3.{self.region_name}.amazonaws.com"
        self.session = session

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        async with self.session.client(
            "s3", region_name=self.region_name, endpoint_url=self.endpoint_url
        ) as s3:
            await s3.put_object(
                Bucket=self.bucket_name, Key=key, Body=content, ContentType=content_type
            )

    async def generate_presigned_url(self, key: str, expires_in: int) -> str:
        async with self.session.client(
            "s3", region_name=self.region_name, endpoint_url=self.endpoint_url
        ) as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expires_in,
            )

    async def delete(self, key: str) -> None:
        async with self.session.client(
            "s3", region_name=self.region_name, endpoint_url=self.endpoint_url
        ) as s3:
            await s3.delete_object(Bucket=self.bucket_name, Key=key)
