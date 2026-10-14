import re

from app.controllers.common.scoped_resource_controller import ScopedResourceController
from app.models.memory.memory import Memory
from app.models.memory.memory_photo import MemoryPhoto
from app.services.memory_photo_service import memory_photo_file_path


class MemoryPhotoController(ScopedResourceController):
    model = MemoryPhoto
    resource_name = "Memory photo"
    set_user_id = False

    def owner_filter(self):
        return MemoryPhoto.memory.has(Memory.user_id == self.user.id)

    def validate_create(self, fields: dict) -> None:
        self.require_owned(
            self.db.query(Memory).filter(
                Memory.id == fields["memory_id"],
                Memory.user_id == self.user.id,
            ),
            "Memory",
        )

    def delete(self, resource_id: int) -> None:
        photo = self.get(resource_id)
        match = re.fullmatch(
            r"/api/v1/memory-photos/files/([0-9a-f]{32}\.(?:png|jpg|gif|webp))",
            photo.image_path,
        )
        super().delete(resource_id)
        if match is not None:
            memory_photo_file_path(match.group(1)).unlink(missing_ok=True)