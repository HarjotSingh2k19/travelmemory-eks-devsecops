const express = require('express')
const cors = require('cors')
require('dotenv').config()

const app = express()
PORT = process.env.PORT
const conn = require('./conn')
app.use(express.json())
app.use(cors())

const tripRoutes = require('./routes/trip.routes')

// Use this to mount the router under the exact path the ALB expects
app.use('/api/trip', tripRoutes);

// Add a simple health check at the new prefix
app.get('/api/hello', (req, res) => {
    res.status(200).send('Hello World!');
});


app.listen(PORT, ()=>{
    console.log(`Server started at http://localhost:${PORT}`)
})


module.exports = app