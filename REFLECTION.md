## Product Images

### Question 1
There was only one time today I had to disagree with CLAUDE and he recommended that I go ahead seed load all the images from the temporary images folder. I know you kind of ened up saying this later in the homework but I hadnt gotten that far yet so it was the only real disagreement I had. If I did listen and go forward with seed then it would have deleted the porducts I had setup and reverted everything back to the defualt products.

### Question 2
PART 1: image = models.ImageField(upload_to="products/", blank=True) I found it in products/models.py on line 78. upload_to just stores the uploaded images in a sub folder in prducts which is set by MEDIA_ROOT. So its basically storing the images path rather than the actual image.

PART 2: form method="post" enctype="multipart/form-data" class="mt-2 space-y-4" Found it in templates/products/manage_products_form.html on line 13. The enctype is needed because it makes sure the actaul file image is sent and without it you wouldnt be able see the image because it wouldnt reach Django.

### Question 3
PART 1: C:\Users\Noah Ellis\cidm3312\thoughttronix-store\media\products\3a3a0238-28bf-4e5f-bee8-188792874284.webp
First the MEDIA_ROOT sets the main upload folder as the media folder and then the Product.image uses upload_to and places it in the products subfolder.

PART 2: products/3a3a0238-28bf-4e5f-bee8-188792874284.webp | The databse will keep the image relative to MEDIA_ROOT but will keep the actual image file on disc and then upload_to will determine the products/ prefix.

PART 3: http://127.0.0.1:8000/media/products/3a3a0238-28bf-4e5f-bee8-188792874284.webp | So it kind of goes back to the two main parts. MEDIA_URL will determine the /media/ part in the url and then the image field will hold the products part and webp part and then when you put them together it will tell the browser where it needs to requests the image so i can show it properly.

PART 4: What makes the media url work during developement is this line of code: 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

This just says when dbug mode is active to handle requests with the media URL by finding the requested file in the media folder

## Featured Products
When I checked the featured box for a product on the admin page, it changed that product's is_featured value in the database. Its setup in products/models.py and both catalog and detail will check if the product featured is true. If it turns out to be true then it will assign the feature badge to it and if its falso then it wont assign the badge to the product.

### Question 2 - How I verified it
I checked it by first searching up and finding each item in the catalog and saw that the featured badge was on those items but not the others. I then also checked inside the details of each of those items and made sure it listed as featured in there too. Lastly, I also ran the full test suite and all tests passed as well.

### Question 3 - Judgment
So I dont know if this really counts because it was technically a problem with the lab instead but it did still take me a while to fix but the biggest problem I had was that the Tailwind build kept failing while my project was inside OneDrive. The error said that the CSS folder already existed, even though it was supposed to be a normal folder. I checked the folder and waited for OneDrive to finish syncing, but the error continued. I eventually cloned my repository into a new cidm3312 folder outside OneDrive, installed the project packages again, and rebuilt the stylesheet. After moving it, the build worked correctly.

### Discount Codes
The expiration-date question was the most confusing decision for me. At first, I thought setting an expiration date would be straightforward, but Claude pointed out that the store was using UTC. That could make a code advertised as valid through September 30 stop working during the evening of September 30 in Texas. I chose an expiration date that lasts through the whole day in the store’s America/Chicago time zone. I followed up by asking whether a code would still work at 11 p.m. Central on its expiration date. This choice made the deadline match what a customer would understand from the promotion.

My original checkout design let customers apply a coupon and see the lower total, but I realized there was no clear way to remove an applied code. That felt awkward if someone changed their mind or wanted to try another code. I asked Claude to add a “Remove code” action. Now removing it clears the code from the order form and restores the original total without erasing the address information. I checked that I could apply a code, remove it, and place an order without a discount. The existing tests did not fail during the build.

