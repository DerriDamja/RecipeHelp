-- Users --
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);



-- User Preferences --
CREATE TABLE IF NOT EXISTS user_diets (
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    diet_id BIGINT NOT NULL REFERENCES diets(diet_id) ON DELETE RESTRICT,
    PRIMARY KEY (user_id, diet_id)
);

CREATE TABLE IF NOT EXISTS user_health_labels (
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    health_label_id BIGINT NOT NULL REFERENCES health_labels(health_label_id) ON DELETE RESTRICT,
    PRIMARY KEY (user_id, health_label_id)
);

CREATE TABLE IF NOT EXISTS user_cuisine_preferences (
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    cuisine_id BIGINT NOT NULL REFERENCES cuisines(cuisine_id) ON DELETE RESTRICT,
    preference TEXT NOT NULL CHECK (preference IN (
        'LOVE',
        'LIKE',
        'EXCLUDE'
    )),
    PRIMARY KEY (user_id, cuisine_id)
);

CREATE TABLE IF NOT EXISTS user_ingredient_preferences (
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    ingredient_id BIGINT NOT NULL REFERENCES ingredients(ingredient_id) ON DELETE RESTRICT,
    preference TEXT NOT NULL CHECK (preference IN (
        'LOVE',
        'LIKE',
        'EXCLUDE'
    )),
    PRIMARY KEY (user_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS user_nutrition_goals (
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    ingredient_id BIGINT NOT NULL REFERENCES nutrients(nutrient_id) ON DELETE RESTRICT,
    min_quantity NUMERIC(12,4) CHECK (min_quantity IS NULL OR min_quantity >= 0),
    max_quantity NUMERIC(12,4) CHECK (max_quantity IS NULL OR max_quantity >= 0),
    CONSTRAINT chk_nutrition_goal_range CHECK(
        min_quantity IS NULL
        OR max_quantity IS NULL
        OR min_quantity <= max_quantity
    ),
    PRIMARY KEY (user_id, ingredient_id)
);



-- Recipes --
CREATE TABLE IF NOT EXISTS recipes (
    recipe_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recipe_name TEXT NOT NULL,
    source_id BIGINT NOT NULL REFERENCES recipe_sources(source_id),
    image_url TEXT,
    servings NUMERIC(8,2) NOT NULL CHECK (servings > 0),
    total_weight_g NUMERIC(12,4) NOT NULL CHECK (total_weight_g > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Recipe Junction Tables --
CREATE TABLE IF NOT EXISTS recipe_sources (
    source_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_url TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id BIGINT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    ingredient_id BIGINT NOT NULL REFERENCES ingredients(ingredient_id) ON DELETE RESTRICT,
    original_text TEXT NOT NULL,
    measure TEXT,
    quantity NUMERIC CHECK (quantity IS NULL OR quantity > 0),
    weight_g NUMERIC CHECK (weight_g IS NULL OR weight_g > 0),
    PRIMARY KEY (recipe_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS recipe_nutrients (
    recipe_id BIGINT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    nutrient_id BIGINT NOT NULL REFERENCES nutrients(nutrient_id) ON DELETE RESTRICT,
    quantity NUMERIC(12, 4) NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (recipe_id, nutrient_id)
);



-- Ingredients --
CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingredient_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);



-- Nutrients --
CREATE TABLE IF NOT EXISTS nutrients (
    nutrient_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nutrient_name TEXT NOT NULL UNIQUE,
    nutrient_tag TEXT NOT NULL UNIQUE,
    unit TEXT NOT NULL
);



-- Recipe Classifications --
CREATE TABLE IF NOT EXISTS diets (
    diet_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    diet_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS health_labels (
    health_label_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    health_label_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS cautions (
    caution_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    caution_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS cuisines (
    cuisine_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cuisine_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS meal_types (
    meal_type_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    meal_type_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dish_types (
    dish_type_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dish_type_name TEXT NOT NULL UNIQUE
);



-- Recipe Classification Junctions --
CREATE TABLE IF NOT EXISTS recipe_diets (
    recipe_id BIGINT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    diet_id BIGINT NOT NULL REFERENCES diets(diet_id) ON DELETE RESTRICT,
    PRIMARY KEY (recipe_id, diet_id)
);

CREATE TABLE IF NOT EXISTS recipe_health_labels (
    recipe_id BIGINT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    health_label_id BIGINT NOT NULL REFERENCES health_labels(health_label_id) ON DELETE RESTRICT,
    PRIMARY KEY (recipe_id, health_label_id)
);

CREATE TABLE IF NOT EXISTS recipe_cautions (
    recipe_id BIGINT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    caution_id BIGINT NOT NULL REFERENCES cautions(caution_id) ON DELETE RESTRICT,
    PRIMARY KEY (recipe_id, caution_id)
);

CREATE TABLE IF NOT EXISTS recipe_cuisines (
    recipe_id BIGINT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    cuisine_id BIGINT NOT NULL REFERENCES cuisines(cuisine_id) ON DELETE RESTRICT,
    PRIMARY KEY (recipe_id, cuisine_id)
);

CREATE TABLE IF NOT EXISTS recipe_meal_types (
    recipe_id BIGINT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    meal_type_id BIGINT NOT NULL REFERENCES meal_types(meal_type_id) ON DELETE RESTRICT,
    PRIMARY KEY (recipe_id, meal_type_id)
);

CREATE TABLE IF NOT EXISTS recipe_dish_types (
    recipe_id BIGINT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    dish_type_id BIGINT NOT NULL REFERENCES dish_types(dish_type_id) ON DELETE RESTRICT,
    PRIMARY KEY (recipe_id, dish_type_id)
);