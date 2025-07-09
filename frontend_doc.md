npm run develop
You will be greeted with the Admin Create Account screen.

003-strapi-5.png

Go ahead and create your first Strapi user. All of this is local so you can use whatever you want.

Once you have created your user, you will be redirected to the Strapi Dashboard screen.

004-strapi-5.png

Publish Article Entries
Since we created our app with the example data, you should be able to navigate to your Article collection and see the data that was created for us.

005-strapi-5.png

Now, let's make sure that all of the data is published. If not, you can select all items via the checkbox and then click the Publish button.

Strapi Articles Published

Enable API Access
Once all your articles are published, we will expose our Strapi API for the Articles Collection. This can be done in Settings -> Users & Permissions plugin -> Roles -> Public -> Article.

You should have find and findOne selected. If not, go ahead and select them.

007-strapi-5.png

Test API
Now, if we make a GET request to http://localhost:1337/api/articles, we should see the following data for our articles.

008-strapi-5.png

🖐️ Note: that article covers (images) are not returned. This is because the REST API by default does not populate any relations, media fields, components, or dynamic zones.. Learn more about REST API: Population & Field Selection.

So let's get the article covers by using the populate=* parameter: http://localhost:1337/api/articles?populate=*

vuejs strapi integration - api request.png

Nice, now that we have our Strapi 5 server setup, we can start to setup our Next.js application.

Creat a Next.js App
It is recommended to use the create-next-app, which sets up everything automatically for you.


npx create-next-app@latest
Depending on your project setup, you will answer the following prompts:


✔ What is your project named? … nextjs-project
✔ Would you like to use TypeScript? … Yes
✔ Would you like to use ESLint? … No
✔ Would you like to use Tailwind CSS? … Yes
✔ Would you like your code inside a `src/` directory? … Yes
✔ Would you like to use App Router? (recommended) … Yes
✔ Would you like to use Turbopack for `next dev`? … Yes
✔ Would you like to customize the import alias (`@/*` by default)? … No
Ensure you select "Yes" for Tailwind CSS.

Start Your Next.js Application
Start Next.js in development mode by running the command below.


npm run dev
Here is what your new Next.js application should look like on the URL http://localhost:3000:

New Nextjs project.png

Use an HTTP Client For Requests
Many HTTP clients are available, but on this integration page, we'll use Axios and Fetch.

Using Axios
Install Axios by running any of the commands below:


# npm
npm i axios

# yarn
yarn add axios
Using fetch
No installation needed

Fetch Contents from Strapi
Execute a GET request on the Article collection type in order to fetch all your articles.

Be sure that you activated the find permission for the Article collection type.

🖐️ NOTE: We want to also fetch covers (images) of articles, so we have to use the populate parameter as seen below.

Using Axios

import axios;

// fetch articles along with their covers
const response = await axios.get("http://localhost:1337/api/articles?populate=*");
console.log(response.data.data);
Using Fetch

const response = await fetch("http://localhost:1337/api/articles?populate=*");
const data = await response.json();
console.log(data.data);
Project Example
In this project example, you will fetch data from Strapi and display them in your Next.js application.

Head over to your Next.js entry file ./src/app/page.tsx to proceed.

Step 1: Specify the "use client" Directory
Inside the ./src/app/page.tsx file, add the code below:


// Path: ./src/app/page.tsx

"use client"; // This is a client-side component
The "use client" directive will tell Next.js to render a component on the client-side instead of the default server directive.

Step 2: Import React hooks and Image component
Import the React hooks useEffect and useState for side effects and state management respectively.

Also, import the Image component which provides automatic image optimization.


"use client"; // This is a client-side component

// Import React hooks and Image component
import { useEffect, useState } from "react";
import Image from "next/image";
Step 3: Allow Images from Localhost in Next.js
Since you are working on a development environment localhost, you have to configure Next.js to allow images.

Navigate to ./next.config.ts and add the following code:


// Path: ./next.config.ts

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */

  // Allow images from localhost
  images: {
    domains: ["localhost"],
  },
};

export default nextConfig;
Step 4: Create Data Type and Constant
Create an interface called Article which represents the data structure of the articles we will fetch from Strapi. Also, create a Strapi URL constant.


export interface Article {
  id: string;
  title: string;
  content: string;
  cover: any;
  publishedAt: Date;
}

// Define Strapi URL
const STRAPI_URL = "http://localhost:1337";
Step 5: Define articles State Variable
Create a state variable articles to hold articles data fetched from Strapi.


// Define articles state
const [articles, setArticles] = useState<Article[]>([]);
Step 6: Create Function to Fetch Articles
Create an asynchronous function that fetches the articles from the Strapi API. The data fetched is passed to setArticles to update the articles state.


const getArticles = async () => {
  const response = await fetch(`${STRAPI_URL}/api/articles?populate=*`);
  const data = await response.json();
  setArticles(data.data);
};
Step 7: Create a Function to Format Dates
Create a helper function to format the publishedAt date of the article into a human-readable format (MM/DD/YYYY).


const formatDate = (date: Date) => {
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  };
  return new Date(date).toLocaleDateString("en-US", options);
};
Step 8: Fetching Articles on Component Mount
Use the useEffect to run the getArticles function when the component mounts.


useEffect(() => {
  getArticles();
}, []);
Step 9: Render and Display Articles

return (
  <div className="p-6">
    <h1 className="text-4xl font-bold mb-8">Next.js and Strapi Integration</h1>
    <div>
      <h2 className="text-2xl font-semibold mb-6">Articles</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {articles.map((article) => (
          <article
            key={article.id}
            className="bg-white shadow-md rounded-lg overflow-hidden"
          >
            <Image
              className="w-full h-48 object-cover"
              src={STRAPI_URL + article.cover.url}
              alt={article.title}
              width={180}
              height={38}
              priority
            />
            <div className="p-4">
              <h3 className="text-lg font-bold mb-2">{article.title}</h3>
              <p className="text-gray-600 mb-4">{article.content}</p>
              <p className="text-sm text-gray-500">
                Published: {formatDate(article.publishedAt)}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  </div>
);
Now, this is what your Next.js project should look like:


Awesome, congratulations!

