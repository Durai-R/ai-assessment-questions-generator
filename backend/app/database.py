from pymongo import ASCENDING, DESCENDING


async def ensure_indexes(database) -> None:
    await database.users.create_index(
        [("email", ASCENDING)],
        unique=True,
        name="users_email_unique",
    )
    await database.questions.create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING), ("_id", DESCENDING)],
        name="questions_user_newest",
    )
    await database.questions.create_index(
        [("user_id", ASCENDING), ("subject", ASCENDING)],
        name="questions_user_subject",
    )
    await database.questions.create_index(
        [("user_id", ASCENDING), ("topic", ASCENDING)],
        name="questions_user_topic",
    )
