import sys
from datetime import datetime
import csv

# ===============================
# Kivy Imports
# ===============================
try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.label import Label
    from kivy.uix.textinput import TextInput
    from kivy.uix.button import Button
    from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
    from kivy.uix.popup import Popup
    from kivy.core.window import Window
    from kivy.metrics import dp, sp
    from kivy.utils import get_color_from_hex
except ImportError as e:
    print("Kivy import error:", e)
    sys.exit(1)

# ===============================
# Window Config
# ===============================
Window.size = (480, 800)
Window.minimum_width = 450
Window.minimum_height = 650

# ===============================
# Global Constants
# ===============================
DEFAULT_LOAN_YEARS = 30
CLOSING_COST_RATE = 0.03
DISPLAY_PAYMENTS_LIMIT = 24

# ======================================================
# Finance Calculations (UNCHANGED CORE)
# ======================================================
class FinanceCalculations:

    @staticmethod
    def calculate_monthly_payment(principal, annual_rate, years):
        if principal <= 0 or years <= 0:
            return 0
        monthly_rate = annual_rate / 100 / 12
        payments = years * 12
        if monthly_rate == 0:
            return principal / payments
        return (principal * monthly_rate * (1 + monthly_rate) ** payments) / \
               ((1 + monthly_rate) ** payments - 1)

    @staticmethod
    def generate_amortization_schedule(loan, rate, years):
        if loan <= 0 or rate <= 0 or years <= 0:
            return []

        payment = FinanceCalculations.calculate_monthly_payment(loan, rate, years)
        monthly_rate = rate / 100 / 12
        balance = loan
        schedule = []

        for i in range(1, years * 12 + 1):
            interest = balance * monthly_rate
            principal = payment - interest
            balance -= principal
            balance = max(balance, 0)

            schedule.append({
                "payment": i,
                "payment_amount": payment,
                "principal": principal,
                "interest": interest,
                "balance": balance
            })

        return schedule

# ======================================================
# Shared Helpers
# ======================================================
def compare_property(price, down, rate, rent, expenses, years=DEFAULT_LOAN_YEARS):
    loan = price - down
    monthly_payment = FinanceCalculations.calculate_monthly_payment(
        loan, rate, years
    )
    monthly_cash_flow = rent - expenses - monthly_payment
    annual_cash_flow = monthly_cash_flow * 12
    investment = down + (price * CLOSING_COST_RATE)

    coc = (annual_cash_flow / investment * 100) if investment > 0 else 0
    cap = ((rent * 12 - expenses * 12) / price * 100) if price > 0 else 0

    return {
        "monthly_payment": monthly_payment,
        "monthly_cash_flow": monthly_cash_flow,
        "coc": coc,
        "cap_rate": cap,
        "investment": investment
    }

# ======================================================
# UI Input Component (UNCHANGED)
# ======================================================
class CleanInput(BoxLayout):

    def __init__(self, label, default="", **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(50), **kwargs)
        self.spacing = dp(5)

        lbl = Label(text=label, size_hint_x=0.45, font_size=sp(15))
        self.input = TextInput(
            text=str(default),
            multiline=False,
            size_hint_x=0.55,
            input_filter="float"
        )

        self.add_widget(lbl)
        self.add_widget(self.input)

    def get_value(self):
        try:
            return float(self.input.text)
        except ValueError:
            return 0.0

# ======================================================
# Mortgage Tab (UNCHANGED)
# ======================================================
class MortgageTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(10), **kwargs)
        self.price = CleanInput("Home Price", 300000)
        self.down = CleanInput("Down Payment", 60000)
        self.rate = CleanInput("Rate %", 4.5)
        self.years = CleanInput("Years", 30)

        for w in [self.price, self.down, self.rate, self.years]:
            self.add_widget(w)

        btn = Button(text="Calculate")
        btn.bind(on_press=self.calculate)
        self.add_widget(btn)

        self.result = Label()
        self.add_widget(self.result)

    def calculate(self, *_):
        loan = self.price.get_value() - self.down.get_value()
        payment = FinanceCalculations.calculate_monthly_payment(
            loan, self.rate.get_value(), int(self.years.get_value())
        )
        self.result.text = f"Monthly Payment: ${payment:,.2f}"


# ======================================================
# Affordability Tab (RESTORED)
# ======================================================
class AffordabilityTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(10), **kwargs)

        self.income = CleanInput("Annual Income", 75000)
        self.debts = CleanInput("Monthly Debts", 500)
        self.down_pct = CleanInput("Down %", 20)
        self.rate = CleanInput("Rate %", 4.5)
        self.years = CleanInput("Years", 30)

        for w in [
            self.income,
            self.debts,
            self.down_pct,
            self.rate,
            self.years
        ]:
            self.add_widget(w)

        btn = Button(text="Calculate")
        btn.bind(on_press=self.calculate)
        self.add_widget(btn)

        self.result = Label(halign="left", valign="top")
        self.result.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        self.add_widget(self.result)

    def calculate(self, *_):
        monthly_income = self.income.get_value() / 12
        max_payment = monthly_income * 0.36 - self.debts.get_value()

        if max_payment <= 0:
            self.result.text = "Not affordable with current debts."
            return

        rate = self.rate.get_value()
        years = int(self.years.get_value())
        down_pct = self.down_pct.get_value() / 100

        monthly_rate = rate / 100 / 12
        payments = years * 12

        if monthly_rate == 0:
            loan = max_payment * payments
        else:
            loan = max_payment / (
                (monthly_rate * (1 + monthly_rate) ** payments) /
                ((1 + monthly_rate) ** payments - 1)
            )

        price = loan / (1 - down_pct)
        down = price * down_pct

        self.result.text = (
            f"Affordable Home Price: ${price:,.0f}\n"
            f"Down Payment: ${down:,.0f}\n"
            f"Loan Amount: ${loan:,.0f}\n"
            f"Max Monthly Payment: ${max_payment:,.2f}"
        )



# ======================================================
# Rental ROI Tab (UNCHANGED)
# ======================================================
class RentalTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(10), **kwargs)
        self.price = CleanInput("Purchase Price", 300000)
        self.down = CleanInput("Down Payment", 75000)
        self.rate = CleanInput("Rate %", 5)
        self.rent = CleanInput("Rent", 2000)
        self.exp = CleanInput("Expenses", 400)

        for w in [self.price, self.down, self.rate, self.rent, self.exp]:
            self.add_widget(w)

        btn = Button(text="Calculate")
        btn.bind(on_press=self.calc)
        self.add_widget(btn)

        self.result = Label()
        self.add_widget(self.result)

    def calc(self, *_):
        data = compare_property(
            self.price.get_value(),
            self.down.get_value(),
            self.rate.get_value(),
            self.rent.get_value(),
            self.exp.get_value()
        )
        self.result.text = f"Cash Flow: ${data['monthly_cash_flow']:.2f}"

# ======================================================
# Compare Tab (FIXED)
# ======================================================
class CompareTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(10), **kwargs)

        self.p1_price = CleanInput("Property1 Price", 300000)
        self.p1_down = CleanInput("Property1 Down", 60000)
        self.p1_rate = CleanInput("Property1 Rate %", 4.5)
        self.p1_rent = CleanInput("Property1 Rent", 2000)
        self.p1_exp = CleanInput("Property1 Expenses", 500)

        self.p2_price = CleanInput("Property2 Price", 250000)
        self.p2_down = CleanInput("Property2 Down", 50000)
        self.p2_rate = CleanInput("Property2 Rate %", 4.5)
        self.p2_rent = CleanInput("Property2 Rent", 1800)
        self.p2_exp = CleanInput("Property2 Expenses", 450)

        for w in [
            self.p1_price, self.p1_down, self.p1_rate, self.p1_rent, self.p1_exp,
            self.p2_price, self.p2_down, self.p2_rate, self.p2_rent, self.p2_exp
        ]:
            self.add_widget(w)

        btn = Button(text="Compare")
        btn.bind(on_press=self.compare)
        self.add_widget(btn)

        self.result = Label()
        self.add_widget(self.result)

    def compare(self, *_):
        p1 = compare_property(
            self.p1_price.get_value(), self.p1_down.get_value(),
            self.p1_rate.get_value(), self.p1_rent.get_value(), self.p1_exp.get_value()
        )
        p2 = compare_property(
            self.p2_price.get_value(), self.p2_down.get_value(),
            self.p2_rate.get_value(), self.p2_rent.get_value(), self.p2_exp.get_value()
        )

        winner = "Property 1" if p1["coc"] > p2["coc"] else "Property 2"

        self.result.text = (
            f"Property1 CoC: {p1['coc']:.2f}%\n"
            f"Property2 CoC: {p2['coc']:.2f}%\n"
            f"Winner: {winner}"
        )

# ======================================================
# Amortization Tab (FIXED)
# ======================================================
class AmortizationTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(10), **kwargs)

        self.loan = CleanInput("Loan", 240000)
        self.rate = CleanInput("Rate %", 4.5)
        self.years = CleanInput("Years", 30)

        for w in [self.loan, self.rate, self.years]:
            self.add_widget(w)

        btns = BoxLayout(size_hint_y=None, height=dp(40))
        gen = Button(text="Generate")
        exp = Button(text="Export CSV")
        gen.bind(on_press=self.generate)
        exp.bind(on_press=self.export)
        btns.add_widget(gen)
        btns.add_widget(exp)
        self.add_widget(btns)

        self.scroll = ScrollView()
        self.box = BoxLayout(orientation="vertical", size_hint_y=None)
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        self.add_widget(self.scroll)

        self.schedule = []

    def generate(self, *_):
        self.box.clear_widgets()
        self.schedule = FinanceCalculations.generate_amortization_schedule(
            self.loan.get_value(), self.rate.get_value(), int(self.years.get_value())
        )

        for p in self.schedule[:DISPLAY_PAYMENTS_LIMIT]:
            self.box.add_widget(Label(
                text=f"{p['payment']} | "
                     f"P {p['principal']:.2f} "
                     f"I {p['interest']:.2f} "
                     f"B {p['balance']:.2f}",
                size_hint_y=None, height=dp(25)
            ))

    def export(self, *_):
        if not self.schedule:
            Popup(title="Error", content=Label(text="Generate first"),
                  size_hint=(0.8, 0.3)).open()
            return

        name = f"amort_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(name, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["#", "Payment", "Principal", "Interest", "Balance"])
            for p in self.schedule:
                writer.writerow([
                    p["payment"],
                    round(p["payment_amount"], 2),
                    round(p["principal"], 2),
                    round(p["interest"], 2),
                    round(p["balance"], 2)
                ])

        Popup(title="Success", content=Label(text=f"Saved {name}"),
              size_hint=(0.8, 0.3)).open()

# ======================================================
# Main App
# ======================================================
class HousingFinanceApp(App):
    def build(self):
        tabs = TabbedPanel(do_default_tab=False)

        tabs.add_widget(TabbedPanelItem(text="Mortgage", content=MortgageTab()))
        tabs.add_widget(TabbedPanelItem(text="Affordability", content=AffordabilityTab()))
        tabs.add_widget(TabbedPanelItem(text="ROI", content=RentalTab()))
        tabs.add_widget(TabbedPanelItem(text="Compare", content=CompareTab()))
        tabs.add_widget(TabbedPanelItem(text="Schedule", content=AmortizationTab()))

        return tabs

# ======================================================
# Run
# ======================================================
if __name__ == "__main__":
    HousingFinanceApp().run()
