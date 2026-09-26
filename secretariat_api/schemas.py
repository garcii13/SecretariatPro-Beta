from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class PasswordResetRequest(BaseModel):
    email: str


class ClipboardPayload(BaseModel):
    text: str = Field(min_length=1, max_length=4096)


class AccountProfileUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)


class AccountPasswordUpdate(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class AccountAvatarUpdate(BaseModel):
    image_data: str = Field(min_length=32)


class ScoreModeRequest(BaseModel):
    mode: Literal["ocr", "manual"] = "ocr"


class ScoreRequest(BaseModel):
    value: int = Field(ge=0, le=999)


class ScoreDeltaRequest(BaseModel):
    delta: int = Field(ge=-50, le=50)


class TimeRequest(BaseModel):
    value: str


class OverlayRequest(BaseModel):
    lineup_team: Literal["team1", "team2"] | None = None


class GraphicsCueRequest(BaseModel):
    panel: str
    lineup_team: Literal["team1", "team2"] = "team1"
    label: str = Field(default="", max_length=80)
    duration_seconds: int = Field(default=0, ge=0, le=120)


class GraphicsCueMoveRequest(BaseModel):
    position: int = Field(ge=0, le=15)


class GraphicsSequenceStep(BaseModel):
    panel: str
    lineup_team: Literal["team1", "team2"] = "team1"
    duration_seconds: int = Field(default=5, ge=1, le=120)
    interval_seconds: int = Field(default=0, ge=0, le=60)


class GraphicsSequenceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    steps: list[GraphicsSequenceStep] = Field(min_length=1, max_length=16)


class PeriodRequest(BaseModel):
    value: int = Field(ge=1, le=20)


class ReplayMarkRequest(BaseModel):
    label: str = Field(default="Replay", min_length=1, max_length=120)
    match_time: str = Field(default="", max_length=20)
    event_id: str = Field(default="", max_length=128)
    team: str = Field(default="", max_length=80)
    player: str = Field(default="", max_length=120)
    post_roll_seconds: float = Field(default=0, ge=0, le=20)


class ReplaySelectionRequest(BaseModel):
    included: bool = True
    label: str = Field(default="", max_length=120)


class HighlightsRequest(BaseModel):
    title: str = Field(default="Highlights", min_length=1, max_length=120)
    clip_ids: list[str] = Field(default_factory=list, max_length=100)


class ReplayCompositionSegment(BaseModel):
    camera: int = Field(ge=1, le=16)
    duration_seconds: int = Field(ge=1, le=60)
    speed_percent: Literal[25, 50, 75, 100] = 100


class ReplayCompositionRequest(BaseModel):
    save_video: bool = True
    clip_id: str = ""
    segments: list[ReplayCompositionSegment] = Field(min_length=0, max_length=6)
    play_now: bool = False
    goal_flow: bool = False


class ReplayTemplateRequest(BaseModel):
    id: str = Field(default="", max_length=80)
    name: str = Field(min_length=1, max_length=80)
    segments: list[ReplayCompositionSegment] = Field(min_length=1, max_length=6)
    default: bool = False


class PowerplayStartRequest(BaseModel):
    player_id: str = Field(min_length=1)
    player_number: str | int | None = None  # ignored; resolved from the saved call-up
    penalty_type: Literal["2", "2+2", "2+10"] = "2"
    serving_player_id: str = ""
    serving_player_number: str | int | None = None  # ignored; resolved from the saved call-up
    current_seconds: int | None = Field(default=None, ge=0)
    register_online: bool = True


class SettingsPatch(BaseModel):
    language: str | None = None
    obs: dict[str, Any] | None = None
    shortcuts: dict[str, str] | None = None
    appearance: dict[str, Any] | None = None
    ocr_data_sharing: bool | None = None


class OCRSourceActivation(BaseModel):
    source_type: Literal["window", "camera"] = "window"
    source_id: str = ""
    source_label: str = ""


class OCRConfigPayload(BaseModel):
    # Phase 52 keeps window_title for backwards compatibility while source_type
    # and source_id allow any OS camera/capture device to feed the same OCR.
    source_type: Literal["window", "camera"] = "window"
    source_id: str = ""
    source_label: str = ""
    window_title: str = ""
    poll_ms: int = Field(default=700, ge=80, le=10000)
    regions: dict[str, Any] = Field(default_factory=dict)
    perspective: dict[str, Any] = Field(default_factory=dict)
    model: dict[str, Any] = Field(default_factory=dict)


class AttendancePayload(BaseModel):
    team1: list[str] = Field(default_factory=list)
    team2: list[str] = Field(default_factory=list)
    starters: dict[str, dict[str, str]] = Field(default_factory=dict)


class GoalPayload(BaseModel):
    marker_id: str = Field(default="", max_length=80)
    score_before: int | None = Field(default=None, ge=0)
    request_id: str = Field(default="", max_length=80)
    team: Literal["team1", "team2"]
    scorer_id: str
    assistant_id: str | None = None
    match_time: str = ""
    increment_manual_score: bool = False




class PlayerProfileRequest(BaseModel):
    team: Literal["team1", "team2"]
    player_id: str = Field(min_length=1)
    show: bool = True

class FinishPayload(BaseModel):
    home_score: int = Field(ge=0, le=999)
    away_score: int = Field(ge=0, le=999)


class PenaltyAttemptRequest(BaseModel):
    outcome: Literal["goal", "miss"] | None = None




class OBSSceneRequest(BaseModel):
    scene_name: str = Field(min_length=1, max_length=256)

class OBSConnectRequest(BaseModel):
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    password: str | None = None
    projector_window: str | None = None

class WorkspaceActivateRequest(BaseModel):
    workspace_id: str = Field(min_length=1)
