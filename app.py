from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import (
    ForeignKey,
    Table,
    Column,
    String,
    Date,
    Float,
    select,
)
from marshmallow import ValidationError, fields
from typing import List
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()

db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")


# initialize flask app
app = Flask(__name__)

# mysql database config
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+mysqlconnector://{db_user}:{db_password}@localhost/ecommerce_api"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# base model
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
db.init_app(app)
ma = Marshmallow(app)


# association table
order_product = Table(
    "order_product",
    Base.metadata,
    Column("order_id", ForeignKey("order.id"), primary_key=True),
    Column("product_id", ForeignKey("product.id"), primary_key=True),
)


# models
class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True)

    # creates one to many relationship to Order
    order: Mapped[List["Order"]] = relationship(back_populates="user")


class Product(Base):
    __tablename__ = "product"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    # creates many to many relationship to Order
    order: Mapped[List["Order"]] = relationship(
        secondary=order_product, back_populates="product"
    )


class Order(Base):
    __tablename__ = "order"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    # creates many to one relationship to user table
    user: Mapped["User"] = relationship(back_populates="order")

    # creates many to many relationship to Product through secondary
    product: Mapped[List["Product"]] = relationship(
        secondary=order_product, back_populates="order"
    )


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User


class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product


class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        include_fk = True


user_schema = UserSchema()
users_schema = UserSchema(many=True)

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)


# retrieves all users
@app.route("/users", methods=["GET"])
def get_users():
    query = select(User)
    users = db.session.execute(query).scalars().all()

    return users_schema.jsonify(users, many=True), 200


# retrieves one user by id
@app.route("/users/<int:id>", methods=["GET"])
def get_user(id):
    user = db.session.get(User, id)  # get users

    return user_schema.jsonify(user), 200


# create new user
@app.route("/users", methods=["POST"])
def create_user():
    try:
        user_data = user_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    new_user = User(
        name=user_data["name"], email=user_data["email"], address=user_data["address"]
    )
    db.session.add(new_user)
    db.session.commit()

    return user_schema.jsonify(new_user), 201


# update user by id PUT
@app.route("/users/<int:id>", methods=["PUT"])
def update_user(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({"message": "Invalid user id"}), 404

    try:
        user_data = user_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    user.name = user_data["name"]
    user.email = user_data["email"]

    db.session.commit()
    return user_schema.jsonify(user), 200


# delete user by id DELETE
@app.route("/users/<int:id>", methods=["DELETE"])
def delete_user(id):
    user = db.session.get(User, id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"successfully deleted user {id}"}), 200


# retrieves all products GET
@app.route("/products", methods=["GET"])
def get_products():
    query = select(Product)
    products = db.session.execute(query).scalars().all()

    return products_schema.jsonify(products, many=True), 200


# retrieves one product by id GET
@app.route("/products/<int:id>", methods=["GET"])
def get_product(id):
    product = db.session.get(Product, id)

    return product_schema.jsonify(product), 200


# create new product POST
@app.route("/products", methods=["POST"])
def create_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    new_product = Product(
        product_name=product_data["product_name"], price=product_data["price"]
    )
    db.session.add(new_product)
    db.session.commit()

    return product_schema.jsonify(new_product), 201


# update product by id PUT /products/<id>
@app.route("/products/<int:id>", methods=["PUT"])
def update_product(id):
    product = db.session.get(Product, id)
    if not product:
        return jsonify({"message": "Invalid product id"}), 404

    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    product.product_name = product_data["product_name"]
    product.price = product_data["price"]

    db.session.commit()
    return product_schema.jsonify(product), 200


# delete product by id DELETE /products/<id>
@app.route("/products/<int:id>", methods=["DELETE"])
def delete_product(id):
    product = db.session.get(Product, id)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": f"successfully deleted product {id}"}), 200


# create new order, requires user_id and order_date
@app.route("/orders", methods=["POST"])
def new_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return (jsonify(e.messages), 400)

    new_order = Order(
        user_id=order_data["user_id"], order_date=order_data["order_date"]
    )

    db.session.add(new_order)
    db.session.commit()

    return order_schema.jsonify(new_order), 201


# add product to an order, prevent duplicates
@app.route("/orders/<int:order_id>/add_product/<int:product_id>", methods=["PUT"])
def add_product(order_id, product_id):
    order = db.session.get(Order, order_id)
    product = db.session.get(Product, product_id)

    # Check if order or product exists
    if not order or not product:
        return jsonify({"error": "Order or Product not found"}), 404

    # Prevent duplicate product in order
    if product in order.product:
        return jsonify({"message": "Product already in order"}), 400

    order.product.append(product)
    db.session.commit()

    return (
        jsonify({"message": f"Successfully added {product.product_name} to order!"}),
        200,
    )


# remove product from an order
@app.route("/orders/<int:order_id>/remove_product/<int:product_id>", methods=["DELETE"])
def remove_product(order_id, product_id):
    order = db.session.get(Order, order_id)
    product = db.session.get(Product, product_id)

    if product not in order.product:
        return jsonify({"error": "Product not found in order"}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": f"successfully deleted {product}"}), 200


# get all orders for a user
@app.route("/orders/user/<int:user_id>", methods=["GET"])
def get_user_orders(user_id):
    query = select(Order).where(Order.user_id == user_id)
    orders = db.session.execute(query).scalars().all()

    return orders_schema.jsonify(orders, many=True), 200


# get all products for an order
@app.route("/orders/<int:order_id>/products", methods=["GET"])
def get_order_products(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    return products_schema.jsonify(order.product), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
