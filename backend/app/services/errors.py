class InvalidImageError(Exception):
    """MIME/拡張子が不正、または画像として開けない。"""


class PayloadTooLargeError(Exception):
    """アップロードサイズが上限を超えた。"""


class NotFoundError(Exception):
    """対象が存在しない。"""
