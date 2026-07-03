FROM node:20-alpine
# Create a non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
# Set permissions
COPY package*.json ./
RUN npm ci --only=production
COPY . .
# Change ownership to the non-root user
RUN chown -R appuser:appgroup /app
USER appuser
EXPOSE 3000
CMD ["node", "index.js"]