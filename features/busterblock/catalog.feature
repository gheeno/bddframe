@web
Feature: VHS Catalog — Scrolling, SVG Badges, and Cart

  Background:
    Given User is on "[BUSTERBLOCK]"
    When User enters [BB_USER] in the username field
    And User enters [BB_PASS] in the password field
    And User clicks the login button
    Then User should see "VHS Catalog"

  @smoke
  Scenario: Catalog loads with movie titles
    Then User should see "Die Hard"
    And User should see "Back to the Future"
    And User should see "Pulp Fiction"

  @smoke
  Scenario: Genre filter narrows the catalog
    When User selects "Action" in the genre filter
    Then User should see "Die Hard"

  @smoke
  Scenario: Search filters movies by title
    When User enters "Terminator" in the search movies field
    Then User should see "The Terminator"

  @smoke
  Scenario: User can add a movie to cart
    When User clicks "Add to Cart"
    Then User should see "1"

  @smoke
  Scenario: SVG genre badges are visible in the catalog
    Then User should see "Thriller"
    And User should see "Sci-Fi"
    And User should see "Horror"

  @smoke
  Scenario: Catalog table scrolls horizontally
    Then User should see "Director"
    And User should see "Runtime"
    And User should see "Format"

  @smoke
  Scenario: User can scroll catalog vertically to see all movies
    Then User should see "Heat"
    And User should see "Speed"
    And User should see "Reservoir Dogs"
