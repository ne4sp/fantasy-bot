from pathlib import Path

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.methods import SendRichMessage
from aiogram.types import InputRichMessage, InputRichBlockDivider, Message, InputRichBlockCollage, InputRichBlockPhoto, InputMediaPhoto
from aiogram.types import FSInputFile, InputRichBlockSlideshow

router = Router(name="feature-tests")
ASSET_DIR = Path(__file__).resolve().parent / "devassets"


@router.message(Command("rich_test1"))
async def rich_test1(message: Message, bot: Bot) -> None:
    await bot(
        SendRichMessage(
            chat_id=message.chat.id,
            rich_message=InputRichMessage(
                blocks=[
                    InputRichBlockPhoto(photo=InputMediaPhoto(media=FSInputFile(ASSET_DIR / "444.jpg"), has_spoiler=True)),
                    InputRichBlockDivider(),
                    InputRichBlockSlideshow(
                                            blocks=[
                                                InputRichBlockPhoto(photo=InputMediaPhoto(media=FSInputFile(ASSET_DIR / "111.jpg"))),
                                                InputRichBlockPhoto(photo=InputMediaPhoto(media=FSInputFile(ASSET_DIR / "222.jpg"))),
                                                InputRichBlockPhoto(photo=InputMediaPhoto(media=FSInputFile(ASSET_DIR / "333.jpg"))),
                                            ]
                                        ),
                    InputRichBlockDivider(),
                    # здесь текстом добавить состояние таблицы фэнтези лиги к этому туру

                ]
            ),
        )
    )
