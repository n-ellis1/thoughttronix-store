## Featured Products
When I checked the featured box for a product on the admin page, it changed that product's is_featured value in the database. Its setup in products/models.py and both catalog and detail will check if the product featured is true. If it turns out to be true then it will assign the feature badge to it and if its falso then it wont assign the badge to the product.

### Question 2 - How I verified it
I checked it by first searching up and finding each item in the catalog and saw that the featured badge was on those items but not the others. I then also checked inside the details of each of those items and made sure it listed as featured in there too. Lastly, I also ran the full test suite and all tests passed as well.

### Question 3 - Judgment
So I dont know if this really counts because it was technically a problem with the lab instead but it did still take me a while to fix but the biggest problem I had was that the Tailwind build kept failing while my project was inside OneDrive. The error said that the CSS folder already existed, even though it was supposed to be a normal folder. I checked the folder and waited for OneDrive to finish syncing, but the error continued. I eventually cloned my repository into a new cidm3312 folder outside OneDrive, installed the project packages again, and rebuilt the stylesheet. After moving it, the build worked correctly.

### Discount Codes
The expiration-date question was the most confusing decision for me. At first, I thought setting an expiration date would be straightforward, but Claude pointed out that the store was using UTC. That could make a code advertised as valid through September 30 stop working during the evening of September 30 in Texas. I chose an expiration date that lasts through the whole day in the store’s America/Chicago time zone. I followed up by asking whether a code would still work at 11 p.m. Central on its expiration date. [Add what Claude told you here.] This choice made the deadline match what a customer would understand from the promotion.

My original checkout design let customers apply a coupon and see the lower total, but I realized there was no clear way to remove an applied code. That felt awkward if someone changed their mind or wanted to try another code. I asked Claude to add a “Remove code” action. Now removing it clears the code from the order form and restores the original total without erasing the address information. I checked that I could apply a code, remove it, and place an order without a discount. The existing tests did not fail during the build.

