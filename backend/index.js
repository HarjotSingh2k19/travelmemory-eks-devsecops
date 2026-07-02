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
apiRouter.use('/api/trip', tripRoutes);
apiRouter.get('/api/hello', (req, res) => { res.send('Hello World!'); });


app.listen(PORT, ()=>{
    console.log(`Server started at http://localhost:${PORT}`)
})


module.exports = app