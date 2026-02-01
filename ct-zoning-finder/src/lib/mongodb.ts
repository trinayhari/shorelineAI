import { MongoClient, Db } from "mongodb";

declare global {
  // eslint-disable-next-line no-var
  var _mongoClientPromise: Promise<MongoClient> | undefined;
}

const uri = process.env.MONGODB_URI || "mongodb://localhost:27017";
const dbName = process.env.MONGODB_DB_NAME || "zoning_rag";

const options = {
  maxPoolSize: 10,
  minPoolSize: 5,
};

let client: MongoClient;
let clientPromise: Promise<MongoClient>;

if (process.env.NODE_ENV === "development") {
  if (!global._mongoClientPromise) {
    client = new MongoClient(uri, options);
    global._mongoClientPromise = client.connect();
  }
  clientPromise = global._mongoClientPromise;
} else {
  client = new MongoClient(uri, options);
  clientPromise = client.connect();
}

export default clientPromise;

export async function getDatabase(): Promise<Db> {
  const client = await clientPromise;
  return client.db(dbName);
}

export async function getChunksCollection() {
  const db = await getDatabase();
  return db.collection("chunks");
}

export async function getParcelsCollection() {
  const db = await getDatabase();
  return db.collection("parcels");
}

export async function getJobsCollection() {
  const db = await getDatabase();
  return db.collection("processing_jobs");
}
