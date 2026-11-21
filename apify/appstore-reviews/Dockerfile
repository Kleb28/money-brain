FROM apify/actor-node:22
COPY package*.json ./
RUN npm install --omit=dev --omit=optional && npm cache clean --force
COPY . ./
CMD ["node", "src/main.js"]
