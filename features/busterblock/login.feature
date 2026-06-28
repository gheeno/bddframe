@web
Feature: BusterBlock Login

  @smoke
  Scenario: Valid user can log in
    Given User is on "[BUSTERBLOCK]"
    When User enters [BB_USER] in the username field
    And User enters [BB_PASS] in the password field
    And User clicks the login button
    Then User should see "VHS Catalog"

  @smoke
  Scenario: Invalid credentials show error
    Given User is on "[BUSTERBLOCK]"
    When User enters "bad_user" in the username field
    And User enters "wrong_pass" in the password field
    And User clicks the login button
    Then User should see "Invalid credentials"

  @smoke
  Scenario Outline: Multiple users can log in independently
    Given User is on "[BUSTERBLOCK]"
    When User enters <username> in the username field
    And User enters <password> in the password field
    And User clicks the login button
    Then User should see "VHS Catalog"

    Examples:
      | username        | password     |
      | reel_ryan       | Popcorn1!    |
      | tape_tanya      | Rewind2#     |
      | vhs_victor      | VCR_3way     |
      | cassette_carl   | Betamax4$    |
      | blockbuster_bea | Eject5%      |
      | rewind_raj      | FastFwd6^    |
      | betamax_bob     | Tracking7&   |
      | player_priya    | Dolby8*      |
      | cinemax_chen    | Surround9(   |
      | admin_ace       | AdminPass0!  |
