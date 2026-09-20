# ThoughtTronix Codebase Map

## 1. The Apps and What Each Owns
Ok the apps are accounts, porducts, orders, and dashboard. The accounts handles most of the stuff with accounts
such as account creation, signing in or out and I think it also identifies what type of user it is. Products is the catalog for all the products and categories and searching for the prodcuts and also the pages used for managing products. Orders is the shopping cart, the completed orders, the checkout, including order history and how the staff hnadles orders. Lastly, dahsboard is like the statistics page basically with all the total orders and total revenue and stuff.
## 2. The Path of One Request
Django will first check config/urls.py which has products/urls.py which has an emoty view that points to catalogview. Since catalogview is in products/views.py it will retrieve the product and send it to templates/products/catalog.html and will then build the page in the browser.
## 3. A Model I Read
I liked the  user model which represents the store user. It uses Django's normal user model but adds something extra. which is an optional job title to distinguish between regular staff and supervisors.
## 4. Deleting a Category
Ok so first the line of code that decides would be on_delete=models.PROTECT. And I think this just protects as the line states, from accidentally deleting categories if products are still assinged to it.
## 5. Where the Tests Live
The tests are organized inside the apps folders meaning each app folder contains its each seperate test files. This is helpful because each app has its own features. The conftest.py is also my answer for quesiton 6 which Ill talk about more but Ill give it a shot on what it does. So i think it has basically like template tests as well as like smaller test things that can request form the template tests instead of making the required thing to test it everytime.
## 6. One Thing I’m Still Working to Understand
So I kind of have two things, The first I already mentioned to be the tests. Im just not fully sure how that works because I understand the sperate test forlders for different apps but the part about the template type tests is wierd. I kind of just took those lines of code and asked what thy were and how they worked and i was sort of close but I think I was wrong aobut there being smaller tests. So the way it works is there are reuasbale pytest fixtures and prepared test objects such as porduct, customer. or employee. Basically tests can request these fixtures  so they dont have to recreate the objects everytime you want to run the tests again.