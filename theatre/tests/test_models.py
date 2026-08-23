from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from theatre.models import Performance, Play, Reservation, TheatreHall, Ticket


class TicketModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="ticket@example.com",
            password="secure-pass-123",
        )
        self.play = Play.objects.create(title="Hamlet", description="A tragedy")
        self.hall = TheatreHall.objects.create(name="Main", rows=3, seats_in_row=4)
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.hall,
            show_time=timezone.now(),
        )
        self.reservation = Reservation.objects.create(user=self.user)

    def test_valid_ticket_is_saved(self):
        ticket = Ticket.objects.create(
            row=3,
            seat=4,
            performance=self.performance,
            reservation=self.reservation,
        )

        self.assertEqual(ticket.row, 3)
        self.assertEqual(ticket.seat, 4)

    def test_ticket_outside_hall_is_rejected(self):
        ticket = Ticket(
            row=4,
            seat=1,
            performance=self.performance,
            reservation=self.reservation,
        )

        with self.assertRaises(ValidationError):
            ticket.save()

