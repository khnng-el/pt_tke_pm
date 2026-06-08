USE `hotel_management`;

START TRANSACTION;

UPDATE `hotels`
SET `descriptions` = 'A beachfront all-inclusive resort on Bai Dai Beach, designed for relaxed family holidays and easy seaside escapes. Guests have direct beach access, bright rooms, ocean-facing views, pools, dining, kids activities and daily services included, making the stay simple from check-in to check-out.'
WHERE `hotel_id` = 1;

UPDATE `hotels`
SET `descriptions` = 'A quiet coastal resort on Cam Ranh Peninsula with low-rise architecture, tropical gardens and direct access to a wide sandy beach. The property focuses on calm, privacy and premium comfort, with ocean-view rooms, spacious villas, breakfast, spa-style relaxation and attentive service for couples or families.'
WHERE `hotel_id` = 2;

UPDATE `hotels`
SET `descriptions` = 'A large beachfront resort between Da Nang and Hoi An, suitable for leisure trips, events and family stays. Guests can enjoy spacious rooms, sea views, a signature pool, restaurants, conference facilities, beach access and reliable resort services in a convenient location near Marble Mountains.'
WHERE `hotel_id` = 3;

UPDATE `hotels`
SET `descriptions` = 'A boutique hotel in the heart of Hanoi Old Quarter, close to Hoan Kiem Lake, weekend walking streets, cafes and local restaurants. Rooms are designed for practical city comfort, supported by breakfast, spa services, room service and friendly front-desk assistance for guests exploring central Hanoi.'
WHERE `hotel_id` = 4;

UPDATE `hotels`
SET `descriptions` = 'A modern boutique hotel in central Hanoi with a clean Scandinavian-inspired style and a calm atmosphere after a busy day in the city. Guests can expect comfortable rooms, smart in-room amenities, breakfast, Wi-Fi and easy access to the Old Quarter, cultural streets, local dining and business areas.'
WHERE `hotel_id` = 5;

UPDATE `hotels`
SET `descriptions` = 'A contemporary hotel in Ha Long with comfortable rooms, bay-inspired views and convenient access to the city waterfront. The property is well suited for short breaks, family trips and business travel, offering breakfast, room service, modern in-room amenities and access to nearby beaches, restaurants and attractions.'
WHERE `hotel_id` = 6;

UPDATE `hotels`
SET `descriptions` = 'A cultural mountain retreat near Yen Tu, created for guests who want quiet scenery, heritage-inspired design and a slower pace. Rooms and suites feel peaceful and atmospheric, with mountain views, spa-style relaxation, breakfast, room service and easy access to spiritual sites, walking paths and nature.'
WHERE `hotel_id` = 7;

UPDATE `hotels`
SET `descriptions` = 'An oceanfront hotel in central Duong Dong, close to the beach, night market, local seafood restaurants and island attractions. Guests can enjoy sea-view rooms, breakfast, pool access, spa-style services, Wi-Fi and a practical location for both relaxing by the water and exploring Phu Quoc.'
WHERE `hotel_id` = 8;

UPDATE `hotels`
SET `descriptions` = 'A private villa resort near Long Beach, designed for families, groups and longer island stays. Villas offer generous living space, private-pool options, kitchen-style comfort, beach access and resort services, giving guests a relaxed base for swimming, dining, celebrations and quiet time in Phu Quoc.'
WHERE `hotel_id` = 9;

UPDATE `hotels`
SET `descriptions` = 'A family-friendly beachfront resort in Cam Ranh with pools, water activities, spacious rooms and relaxed resort facilities. The property works well for couples, families and group holidays, offering breakfast, beach access, dining, kids-friendly spaces and comfortable rooms close to Cam Ranh International Airport.'
WHERE `hotel_id` = 10;

COMMIT;

SELECT `hotel_id`, CHAR_LENGTH(COALESCE(`descriptions`, '')) AS `description_length`
FROM `hotels`
ORDER BY `hotel_id`;
