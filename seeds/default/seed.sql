-- Default seed data for the idp-testing demo application.
-- Run via: make seed  (requires DATABASE_URL to be set)

BEGIN;

-- Categories
INSERT INTO categories (name, slug) VALUES
  ('Electronics',   'electronics'),
  ('Clothing',      'clothing'),
  ('Books',         'books'),
  ('Home & Garden', 'home-garden'),
  ('Sports',        'sports')
ON CONFLICT (slug) DO NOTHING;

-- Products
INSERT INTO products (name, description, category_id, price, stock, discount_pct) VALUES
  ('Wireless Headphones',
   'Premium noise-cancelling headphones with 30h battery life.',
   (SELECT id FROM categories WHERE slug='electronics'), 199.99, 12, 10.0),

  ('Mechanical Keyboard',
   'Tactile switches, RGB backlight, USB-C connectivity.',
   (SELECT id FROM categories WHERE slug='electronics'), 129.99, 8, 0.0),

  ('USB-C Hub 7-in-1',
   'HDMI 4K, 3×USB-A, SD card, 100W PD passthrough.',
   (SELECT id FROM categories WHERE slug='electronics'), 49.99, 25, 15.0),

  ('Cotton T-Shirt — Navy',
   '100% organic cotton, pre-shrunk, available in S-XXL.',
   (SELECT id FROM categories WHERE slug='clothing'), 24.99, 50, 0.0),

  ('Running Jacket',
   'Windproof, water-resistant, reflective strips.',
   (SELECT id FROM categories WHERE slug='clothing'), 89.99, 6, 20.0),

  ('Clean Code',
   'A handbook of agile software craftsmanship by Robert C. Martin.',
   (SELECT id FROM categories WHERE slug='books'), 34.99, 20, 0.0),

  ('The Pragmatic Programmer',
   'From journeyman to master. 20th anniversary edition.',
   (SELECT id FROM categories WHERE slug='books'), 39.99, 15, 5.0),

  ('Garden Kneeler',
   'Foam-padded, foldable, converts to garden seat.',
   (SELECT id FROM categories WHERE slug='home-garden'), 19.99, 30, 0.0),

  ('Yoga Mat — 6mm',
   'Non-slip surface, eco-friendly TPE material.',
   (SELECT id FROM categories WHERE slug='sports'), 29.99, 40, 0.0),

  ('Resistance Band Set',
   'Five levels from 10 to 50 lbs, includes carry bag.',
   (SELECT id FROM categories WHERE slug='sports'), 18.99, 35, 25.0)
ON CONFLICT DO NOTHING;

-- Reviews
INSERT INTO reviews (product_id, author, rating, comment) VALUES
  ((SELECT id FROM products WHERE name='Wireless Headphones'), 'alice',   5, 'Exceptional sound quality and very comfortable for long sessions.'),
  ((SELECT id FROM products WHERE name='Wireless Headphones'), 'bob',     4, 'Great headphones, slight hiss on max volume but otherwise perfect.'),
  ((SELECT id FROM products WHERE name='Mechanical Keyboard'), 'charlie', 5, 'Best keyboard I have ever owned. The tactile feedback is satisfying.'),
  ((SELECT id FROM products WHERE name='USB-C Hub 7-in-1'),   'diana',   4, 'Solid build quality. HDMI works flawlessly with my monitor.'),
  ((SELECT id FROM products WHERE name='Clean Code'),          'eve',     5, 'Mandatory reading for every developer. Changed how I think about code.'),
  ((SELECT id FROM products WHERE name='Yoga Mat — 6mm'),      'frank',   5, 'Non-slip even when sweaty. Very happy with this purchase.')
ON CONFLICT DO NOTHING;

-- One baseline order
INSERT INTO orders (product_id, quantity, status) VALUES
  ((SELECT id FROM products WHERE name='Wireless Headphones'), 1, 'paid')
ON CONFLICT DO NOTHING;

COMMIT;
