const express = require('express')
const cors = require('cors')
require('dotenv').config()

const app = express()
PORT = process.env.PORT
const conn = require('./conn')
app.use(express.json())
app.use(cors())

const tripRoutes = require('./routes/trip.routes')
const apiRouter = express.Router();

// Mount all existing routes onto the API router
apiRouter.use('/trip', tripRoutes);
apiRouter.get('/hello', (req, res) => { res.send('Hello World!'); });

// Mount the apiRouter under the /api prefix
app.use('/api', apiRouter); // Now your backend listens for /api/trip and /api/hello

app.listen(PORT, ()=>{
    console.log(`Server started at http://localhost:${PORT}`)
})


module.exports = app