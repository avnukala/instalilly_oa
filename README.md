## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

# Backend 

To start the backend server, cd into the src directory and run:

### `uvicorn api:app --reload`

# API Keys

Under both the part_scraper and src/api folders, create a 'secret.py'file. Inside the file insert the following:

```
OPENAI_API_KEY='your-api-key-here'
PINECONE_API_KEY = '54e65315-9ea3-490b-a883-ec6cee68aa92'
```

I've included my pinecone api key here so you can immediately start using the chatbot after \
setting the api keys and installing the requirements. 
