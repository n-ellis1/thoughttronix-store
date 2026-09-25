"""Cart and checkout views — thin per the architecture convention.

The three HTMX interactions of the core live here: add-to-cart, quantity
change, and line removal. Each renders a partial (never ``base.html``);
the responses carry the navbar badge as an out-of-band swap via the
``oob_badge`` context flag. Checkout is conventional full-page work:
validate the form, hand everything to ``place_order``. The saved-addresses
feature adds a fourth HTMX interaction — the checkout address picker —
and the full-page My Addresses views.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import StaffRequiredMixin
from products.models import Product

from .forms import AddressForm, CheckoutForm, OrderStatusForm
from .models import Address, Cart, CartItem, Order
from .services import place_order

ADDRESS_SECTIONS = ("shipping", "billing")


class CartView(LoginRequiredMixin, TemplateView):
    """The customer's cart page."""

    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart"] = Cart.for_user(self.request.user)
        return context


class AddToCartView(LoginRequiredMixin, View):
    """HTMX: add a product; the button swaps and the badge updates OOB.

    Looks the product up through ``available()``, so adding an
    unavailable product 404s — the same not-for-sale semantics as the
    public catalog.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product.objects.available(), pk=pk)
        item = Cart.for_user(request.user).add(product)
        return render(
            request,
            "orders/partials/_add_button.html",
            {"product": product, "in_cart": item.quantity, "oob_badge": True},
        )


class CartItemActionView(LoginRequiredMixin, View):
    """Base for HTMX line mutations: act, then re-render the cart contents.

    Items are always fetched through the owner's cart — never by bare pk.
    """

    def post(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        self.act(item)
        return render(
            request,
            "orders/partials/_cart_contents.html",
            {"cart": item.cart, "oob_badge": True},
        )

    def act(self, item):
        raise NotImplementedError


class IncrementCartItemView(CartItemActionView):
    def act(self, item):
        item.increment()


class DecrementCartItemView(CartItemActionView):
    def act(self, item):
        item.decrement()


class RemoveCartItemView(CartItemActionView):
    def act(self, item):
        item.delete()


class CheckoutView(LoginRequiredMixin, FormView):
    """The single checkout page: validate the form, hand off to the service.

    A cart that can't check out (empty, or holding a product that has
    since become unavailable) is sent back to the cart page to be fixed —
    ``place_order`` enforces the same rules transactionally as the
    backstop.
    """

    template_name = "orders/checkout.html"
    form_class = CheckoutForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        cart = Cart.for_user(request.user)
        if not cart.items.exists():
            messages.info(request, "Your cart is empty — add something first.")
            return redirect("orders:cart")
        unavailable = [
            line.product.name for line in cart.lines() if not line.product.is_available
        ]
        if unavailable:
            messages.warning(
                request,
                f"No longer available: {', '.join(unavailable)}. "
                "Remove them from the cart to check out.",
            )
            return redirect("orders:cart")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Pre-fill both sections from the default address.

        The Save boxes start ticked only for a customer with no saved
        addresses yet — returning customers opt in per order.
        """
        initial = super().get_initial()
        addresses = self.request.user.addresses.all()
        default = addresses.filter(is_default=True).first()
        if default:
            for section in ADDRESS_SECTIONS:
                initial.update(default.as_initial(section))
        has_addresses = addresses.exists()
        for section in ADDRESS_SECTIONS:
            initial[f"save_{section}_address"] = not has_addresses
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart"] = Cart.for_user(self.request.user)
        context["saved_addresses"] = self.request.user.addresses.all()
        return context

    def form_valid(self, form):
        cart = Cart.for_user(self.request.user)
        order = place_order(cart, self.request.user, form.cleaned_data)
        # Only after the order succeeds: an address is saved for a real order.
        for section in ADDRESS_SECTIONS:
            if form.cleaned_data[f"save_{section}_address"]:
                Address.objects.save_for(self.request.user, form.cleaned_data, section)
        messages.success(self.request, f"Order {order.number} placed. Thank you!")
        return redirect(reverse("orders:confirmation", kwargs={"pk": order.pk}))


class CheckoutAddressFieldsView(LoginRequiredMixin, View):
    """HTMX: fill one checkout address section from a saved address.

    ``section`` is ``shipping`` or ``billing``; ``?address=`` is the saved
    address pk, looked up through the owner — anyone else's pk 404s.
    """

    def get(self, request, section):
        pk = request.GET.get("address", "")
        if section not in ADDRESS_SECTIONS or not pk.isdigit():
            raise Http404
        address = get_object_or_404(Address, pk=pk, user=request.user)
        form = CheckoutForm(initial=address.as_initial(section))
        fields = getattr(form, f"{section}_fields")()
        return render(
            request, "orders/partials/_address_fields.html", {"fields": fields}
        )


# --- My Addresses ------------------------------------------------------------
#
# The customer's address book: conventional full-page CRUD. Checkout reads
# it; the model keeps the one-default rule.


class OwnAddressesMixin(LoginRequiredMixin):
    """Addresses are always fetched through the owner — never by bare pk."""

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressListView(OwnAddressesMixin, ListView):
    """Saved addresses, default first, then newest."""

    template_name = "orders/address_list.html"
    context_object_name = "addresses"


class AddressCreateView(LoginRequiredMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = "orders/address_form.html"
    success_url = reverse_lazy("orders:addresses")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Address saved.")
        return super().form_valid(form)


class AddressUpdateView(OwnAddressesMixin, UpdateView):
    form_class = AddressForm
    template_name = "orders/address_form.html"
    success_url = reverse_lazy("orders:addresses")

    def form_valid(self, form):
        messages.success(self.request, "Address updated.")
        return super().form_valid(form)


class AddressDeleteView(OwnAddressesMixin, DeleteView):
    """Confirm, then delete — ``Address.delete()`` promotes a new default."""

    template_name = "orders/address_confirm_delete.html"
    context_object_name = "address"
    success_url = reverse_lazy("orders:addresses")

    def form_valid(self, form):
        messages.success(self.request, "Address deleted.")
        return super().form_valid(form)


class MakeDefaultAddressView(LoginRequiredMixin, View):
    """POST-only: make one of the customer's addresses their default."""

    def post(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.make_default()
        messages.success(request, "Default address updated.")
        return redirect("orders:addresses")


class OwnOrdersMixin(LoginRequiredMixin):
    """Orders are always fetched through the owner — never by bare pk."""

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderConfirmationView(OwnOrdersMixin, DetailView):
    template_name = "orders/confirmation.html"
    context_object_name = "order"


class OrderHistoryView(OwnOrdersMixin, ListView):
    """The customer's orders, most recent first per the model ordering."""

    template_name = "orders/order_history.html"
    context_object_name = "orders"


class OrderDetailView(OwnOrdersMixin, DetailView):
    template_name = "orders/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("items")


# --- The back office --------------------------------------------------------
#
# Staff-only order oversight: every customer's orders, filterable by
# status, with the status dropdown on the detail page. The ``section``
# context entry drives the active tab in the staff shell.


class ManageOrderListView(StaffRequiredMixin, ListView):
    """All orders, most recent first, filterable via ``?status=``."""

    template_name = "orders/manage_orders.html"
    context_object_name = "orders"
    paginate_by = 20
    extra_context = {"section": "orders"}

    def get_queryset(self):
        orders = Order.objects.select_related("user")
        status = self.request.GET.get("status", "")
        if status in Order.Status.values:
            orders = orders.filter(status=status)
        return orders

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Order.Status.choices
        context["active_status"] = self.request.GET.get("status", "")
        return context


class ManageOrderDetailView(StaffRequiredMixin, DetailView):
    """Any order's detail, with the status form alongside."""

    template_name = "orders/manage_order_detail.html"
    context_object_name = "order"
    queryset = Order.objects.select_related("user").prefetch_related("items")
    extra_context = {"section": "orders"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_form"] = OrderStatusForm(instance=self.object)
        return context


class UpdateOrderStatusView(StaffRequiredMixin, View):
    """POST-only: set an order's status from the back-office dropdown."""

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"{order.number} is now {order.get_status_display().lower()}.",
            )
        else:
            messages.error(request, "That isn't a status an order can have.")
        return redirect("orders:manage_order_detail", pk=order.pk)
