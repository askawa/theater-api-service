from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from theatre.models import (
    Actor,
    Genre,
    Performance,
    Play,
    Reservation,
    TheatreHall,
    Ticket,
)


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class ActorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name", "full_name")


class PlaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Play
        fields = ("id", "title", "description", "genres", "actors", "image")


class PlayListSerializer(PlaySerializer):
    genres = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    actors = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="full_name",
    )


class PlayDetailSerializer(PlaySerializer):
    genres = GenreSerializer(many=True, read_only=True)
    actors = ActorSerializer(many=True, read_only=True)


class PlayImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Play
        fields = ("id", "image")
        read_only_fields = ("id",)


class TheatreHallSerializer(serializers.ModelSerializer):
    capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = TheatreHall
        fields = ("id", "name", "rows", "seats_in_row", "capacity")


class PerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performance
        fields = ("id", "play", "theatre_hall", "show_time")


class PerformanceListSerializer(PerformanceSerializer):
    play_title = serializers.CharField(source="play.title", read_only=True)
    theatre_hall_name = serializers.CharField(
        source="theatre_hall.name",
        read_only=True,
    )
    available_seats = serializers.SerializerMethodField()

    class Meta(PerformanceSerializer.Meta):
        fields = PerformanceSerializer.Meta.fields + (
            "play_title",
            "theatre_hall_name",
            "available_seats",
        )

    def get_available_seats(self, obj: Performance) -> int:
        tickets_count = getattr(obj, "tickets_count", None)
        if tickets_count is None:
            tickets_count = obj.tickets.count()
        return obj.theatre_hall.capacity - tickets_count


class PerformanceDetailSerializer(PerformanceListSerializer):
    play = PlayListSerializer(read_only=True)
    theatre_hall = TheatreHallSerializer(read_only=True)
    taken_places = serializers.SerializerMethodField()

    class Meta(PerformanceListSerializer.Meta):
        fields = PerformanceListSerializer.Meta.fields + ("taken_places",)

    def get_taken_places(self, obj: Performance) -> list[dict[str, int]]:
        return list(obj.tickets.order_by("row", "seat").values("row", "seat"))


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "performance")
        read_only_fields = ("id",)

    def validate(self, attrs):
        data = super().validate(attrs)
        performance = data.get("performance") or getattr(
            self.instance,
            "performance",
            None,
        )
        row = data.get("row", getattr(self.instance, "row", None))
        seat = data.get("seat", getattr(self.instance, "seat", None))

        if performance and row is not None and seat is not None:
            try:
                Ticket.validate_ticket(row, seat, performance.theatre_hall)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.message_dict) from exc

        return data


class TicketReadSerializer(TicketSerializer):
    play = serializers.CharField(source="performance.play.title", read_only=True)
    theatre_hall = serializers.CharField(
        source="performance.theatre_hall.name",
        read_only=True,
    )
    show_time = serializers.DateTimeField(
        source="performance.show_time",
        read_only=True,
    )

    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + (
            "play",
            "theatre_hall",
            "show_time",
        )


class ReservationSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, allow_empty=False)

    class Meta:
        model = Reservation
        fields = ("id", "created_at", "tickets")
        read_only_fields = ("id", "created_at")

    def validate_tickets(self, tickets):
        places = [
            (ticket["performance"].pk, ticket["row"], ticket["seat"])
            for ticket in tickets
        ]
        if len(places) != len(set(places)):
            raise serializers.ValidationError(
                "The same performance seat cannot be included more than once."
            )

        occupied = Ticket.objects.filter(
            performance_id__in={place[0] for place in places}
        ).values_list("performance_id", "row", "seat")
        occupied_places = set(occupied)
        conflicts = [place for place in places if place in occupied_places]
        if conflicts:
            raise serializers.ValidationError(
                "One or more selected seats have already been reserved."
            )
        return tickets

    def create(self, validated_data):
        tickets_data = validated_data.pop("tickets")
        try:
            with transaction.atomic():
                reservation = Reservation.objects.create(**validated_data)
                for ticket_data in tickets_data:
                    Ticket.objects.create(
                        reservation=reservation,
                        **ticket_data,
                    )
                return reservation
        except (IntegrityError, DjangoValidationError) as exc:
            raise serializers.ValidationError(
                {"tickets": "One or more selected seats are no longer available."}
            ) from exc


class ReservationListSerializer(serializers.ModelSerializer):
    tickets = TicketReadSerializer(many=True, read_only=True)

    class Meta:
        model = Reservation
        fields = ("id", "created_at", "tickets")
