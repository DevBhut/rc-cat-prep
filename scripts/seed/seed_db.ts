import { sql } from '@vercel/postgres';
import fs from 'fs/promises';
import path from 'path';

async function seed() {
  const schemaPath = path.join(process.cwd(), 'scripts', 'seed', 'schema.sql');
  const schema = await fs.readFile(schemaPath, 'utf-8');

  // Split by semicolons and execute each statement
  const statements = schema
    .split(';')
    .map(s => s.trim())
    .filter(s => s.length > 0);

  for (const statement of statements) {
    await sql`${statement}`;
  }

  console.log('Database seeded successfully');
}

seed().catch(console.error);
