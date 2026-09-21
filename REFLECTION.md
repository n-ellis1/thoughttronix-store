## Featured Products
When I checked the featured box for a product on the admin page, it changed that product's is_featured value in the database. Its setup in products/models.py and both catalog and detail will check if the product featured is true. If it turns out to be true then it will assign the feature badge to it and if its falso then it wont assign the badge to the product.

### Question 2 - How I verified it
I checked it by first searching up and finding each item in the catalog and saw that the featured badge was on those items but not the others. I then also checked inside the details of each of those items and made sure it listed as featured in there too. Lastly, I also ran the full test suite and all tests passed as well.

### Question 3 - Judgment
So I dont know if this really counts because it was technically a problem with the lab instead but it did still take me a while to fix but the biggest problem I had was that the Tailwind build kept failing while my project was inside OneDrive. The error said that the CSS folder already existed, even though it was supposed to be a normal folder. I checked the folder and waited for OneDrive to finish syncing, but the error continued. I eventually cloned my repository into a new cidm3312 folder outside OneDrive, installed the project packages again, and rebuilt the stylesheet. After moving it, the build worked correctly.