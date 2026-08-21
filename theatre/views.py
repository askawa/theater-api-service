from datetime import datetime

from django.db.models import Count, QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from theatre.models import Actor, Genre, Performance, Play, Reservation, TheatreHall
from theatre.permissions import IsAdminOrReadOnly
from theatre.serializers import (
    ActorSerializer,
    GenreSerializer,
    PerformanceDetailSerializer,
    PerformanceListSerializer,
    PerformanceSerializer,
    PlayDetailSerializer,
    PlayImageSerializer,
    PlayListSerializer,
    PlaySerializer,
    ReservationListSerializer,
    ReservationSerializer,
    TheatreHallSerializer,
)


def parse_comma_separated_ids(value: str | None, field_name: str) -> list[int]:
    if not value:
        return []
    try:
        return [int(item) for item in value.split(",") if item]
    except ValueError as exc:
        raise serializers.ValidationError(
            {field_name: "Provide a comma-separated list of integer IDs."}
        ) from exc


@extend_schema_view(
    list=extend_schema(tags=["Genres"]),
    retrieve=extend_schema(tags=["Genres"]),
    create=extend_schema(tags=["Genres"]),
    update=extend_schema(tags=["Genres"]),
    partial_update=extend_schema(tags=["Genres"]),
    destroy=extend_schema(tags=["Genres"]),
)
class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrReadOnly,)


@extend_schema_view(
    list=extend_schema(tags=["Actors"]),
    retrieve=extend_schema(tags=["Actors"]),
    create=extend_schema(tags=["Actors"]),
    update=extend_schema(tags=["Actors"]),
    partial_update=extend_schema(tags=["Actors"]),
    destroy=extend_schema(tags=["Actors"]),
)
class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrReadOnly,)


@extend_schema_view(
    list=extend_schema(
        tags=["Plays"],
        parameters=[
            OpenApiParameter("title", str, description="Filter by title fragment"),
            OpenApiParameter(
                "genres",
                str,
                description="Comma-separated genre IDs",
            ),
            OpenApiParameter(
                "actors",
                str,
                description="Comma-separated actor IDs",
            ),
        ],
    ),
    retrieve=extend_schema(tags=["Plays"]),
    create=extend_schema(tags=["Plays"]),
    update=extend_schema(tags=["Plays"]),
    partial_update=extend_schema(tags=["Plays"]),
    destroy=extend_schema(tags=["Plays"]),
)
class PlayViewSet(viewsets.ModelViewSet):
    queryset = Play.objects.prefetch_related("genres", "actors")
    serializer_class = PlaySerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self) -> QuerySet[Play]:
        queryset = self.queryset
        title = self.request.query_params.get("title")
        genre_ids = parse_comma_separated_ids(
            self.request.query_params.get("genres"),
            "genres",
        )
        actor_ids = parse_comma_separated_ids(
            self.request.query_params.get("actors"),
            "actors",
        )

        if title:
            queryset = queryset.filter(title__icontains=title)
        if genre_ids:
            queryset = queryset.filter(genres__id__in=genre_ids)
        if actor_ids:
            queryset = queryset.filter(actors__id__in=actor_ids)
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return PlayListSerializer
        if self.action == "retrieve":
            return PlayDetailSerializer
        if self.action == "upload_image":
            return PlayImageSerializer
        return PlaySerializer

    @extend_schema(tags=["Plays"], request=PlayImageSerializer)
    @action(methods=("post",), detail=True, url_path="upload-image")
    def upload_image(self, request, pk=None):
        play = self.get_object()
        serializer = self.get_serializer(play, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=["Theatre halls"]),
    retrieve=extend_schema(tags=["Theatre halls"]),
    create=extend_schema(tags=["Theatre halls"]),
    update=extend_schema(tags=["Theatre halls"]),
    partial_update=extend_schema(tags=["Theatre halls"]),
    destroy=extend_schema(tags=["Theatre halls"]),
)
class TheatreHallViewSet(viewsets.ModelViewSet):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer
    permission_classes = (IsAdminOrReadOnly,)


@extend_schema_view(
    list=extend_schema(
        tags=["Performances"],
        parameters=[
            OpenApiParameter("date", str, description="Show date in YYYY-MM-DD"),
            OpenApiParameter("play", int, description="Play ID"),
        ],
    ),
    retrieve=extend_schema(tags=["Performances"]),
    create=extend_schema(tags=["Performances"]),
    update=extend_schema(tags=["Performances"]),
    partial_update=extend_schema(tags=["Performances"]),
    destroy=extend_schema(tags=["Performances"]),
)
class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = (
        Performance.objects.select_related("play", "theatre_hall")
        .prefetch_related("play__genres", "play__actors", "tickets")
        .annotate(tickets_count=Count("tickets"))
    )
    serializer_class = PerformanceSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self) -> QuerySet[Performance]:
        queryset = self.queryset
        date_value = self.request.query_params.get("date")
        play_id = self.request.query_params.get("play")

        if date_value:
            try:
                show_date = datetime.strptime(date_value, "%Y-%m-%d").date()
            except ValueError as exc:
                raise serializers.ValidationError(
                    {"date": "Use YYYY-MM-DD date format."}
                ) from exc
            queryset = queryset.filter(show_time__date=show_date)
        if play_id:
            try:
                queryset = queryset.filter(play_id=int(play_id))
            except ValueError as exc:
                raise serializers.ValidationError(
                    {"play": "Provide an integer play ID."}
                ) from exc
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceListSerializer
        if self.action == "retrieve":
            return PerformanceDetailSerializer
        return PerformanceSerializer


@extend_schema_view(
    list=extend_schema(tags=["Reservations"]),
    retrieve=extend_schema(tags=["Reservations"]),
    create=extend_schema(tags=["Reservations"]),
)
class ReservationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Reservation.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_queryset(self) -> QuerySet[Reservation]:
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        return (
            self.queryset.filter(user=self.request.user)
            .prefetch_related(
                "tickets__performance__play",
                "tickets__performance__theatre_hall",
            )
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ReservationSerializer
        return ReservationListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
