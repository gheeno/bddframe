@web
Feature: Run a custom script as a Gherkin step
  # Sometimes a test needs to do something the browser can't — seed a database,
  # run a Java jar, call a shell tool. BDDFrame can invoke any external script or
  # command as a step. The interpreter is inferred from the file extension
  # (.py → python, .js → node, .jar → java -jar, .sh → bash, …); a non-zero exit
  # fails the step. stdout is captured into `SCRIPT_OUTPUT`, so a later step can
  # assert on the result. See README → "Run a script from a step".
  #
  # Phrasings:
  #   Given the script "path/to/x.py" runs
  #   Given run the script "x.py" with "--flag val" storing the output as `RESULT`
  #   Given run the command "java -jar tool.jar [BUSTERBLOCK]"
  #
  # This example mirrors the classic "seed data, then assert it" flow: a Python
  # script forces a movie out of stock, then the UI is checked for that state.

  @smoke
  Scenario: A Python script seeds data, then the UI reflects it
    Given the script "features/busterblock/scripts/seed_out_of_stock.py" runs
    And `SCRIPT_OUTPUT` should contain "OUT OF STOCK"

    When User is on "[BUSTERBLOCK]"
    And User enters [BB_USER] in the username field
    And User enters [BB_PASS] in the password field
    And User clicks the login button
    And User waits until "VHS Catalog" appears
    Then the cell in row "Jaws" column "Stock" should be "Out"
