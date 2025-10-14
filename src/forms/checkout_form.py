from flask_wtf import FlaskForm
from wtforms import SubmitField

class CheckoutForm(FlaskForm):
    submit = SubmitField("Finalizar Compra")
