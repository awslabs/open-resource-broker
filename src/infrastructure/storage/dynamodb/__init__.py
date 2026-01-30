"""DynamoDB storage package."""

from providers.aws.storage.dynamodb.unit_of_work import DynamoDBUnitOfWork

__all__: list[str] = ["DynamoDBUnitOfWork"]
