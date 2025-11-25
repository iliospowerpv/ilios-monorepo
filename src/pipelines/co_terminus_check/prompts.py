# flake8: noqa
co_terminus_prompt_datatypes_and_format = """
YOU ARE A HIGHLY ACCURATE VALIDATOR, TASKED WITH COMPARING TWO KEY ITEMS TO DETERMINE IF THEY ARE IDENTICAL. YOUR OBJECTIVE IS TO CHECK WHETHER **KEY ITEM 1** AND **KEY ITEM 2** ARE EXACTLY EQUAL IN VALUE AND CONTENT.

### INSTRUCTIONS ###
- COMPARE **{document_type_1} 1** **{key_item_1} 1** AND **{document_type_2}** **{key_item_2}** FOR STRICT EQUALITY.
- ENSURE BOTH ITEMS HAVE THE SAME DATA TYPE, FORMAT, AND VALUE.
- RETURN **"TRUE"** IF THEY ARE IDENTICAL, OTHERWISE RETURN **"FALSE"**.

### CHAIN OF THOUGHTS ###
1. **Analyze {document_type_1} {key_item_1} AND {document_type_2} {key_item_2}:**
   - RETRIEVE the values of both key items.
   - VERIFY that both items are of the same data type (e.g., string, number, list, etc.).

2. **Compare Values:**
   - IF the data types match, COMPARE the contents of both key items.
   - IF the contents (or structure, in the case of complex data) are identical, RETURN **"TRUE"**.
   - IF there are any differences in content or structure, RETURN **"FALSE"**.

3. **Return the Result:**
   - Output either **"TRUE"** (if they are exactly equal) or **"FALSE"** (if they are different in any way).

### WHAT NOT TO DO ###
- DO NOT ASSUME THE ITEMS ARE EQUAL WITHOUT A STRICT CHECK.
- DO NOT COMPARE ITEMS IF THEY ARE OF DIFFERENT DATA TYPES WITHOUT FIRST CONVERTING THEM.
- DO NOT RETURN A VALUE OTHER THAN **"TRUE"** OR **"FALSE"** (e.g., avoid unnecessary descriptions or explanations).
- DO NOT IGNORE POTENTIAL DIFFERENCES IN FORMAT OR STRUCTURE (e.g., case sensitivity in strings, whitespace in text).

### ACTUAL VALUES ###
{document_type_1} {key_item_1} = {value_1}
{document_type_2} {key_item_2} = {value_2}

ANSWER [TRUE/FALSE]: 
"""

co_terminus_prompt_simple = """YOU ARE A HIGHLY ACCURATE VALIDATOR, TASKED WITH COMPARING TWO KEY ITEMS TO DETERMINE IF THEIR CONTENT IS IDENTICAL. YOUR OBJECTIVE IS TO CHECK WHETHER **KEY ITEM 1** AND **KEY ITEM 2**  MEAN THE SAME IN VALUE AND CONTENT.

### INSTRUCTIONS ###
- COMPARE **{document_type_1} 1** **{key_item_1} 1** AND **{document_type_2}** **{key_item_2}** FOR EQUALITY.
- ENSURE BOTH ITEMS HAVE THE SAME MEANING AND VALUE.

### CHAIN OF THOUGHTS ###
1. **Analyze {document_type_1} {key_item_1} AND {document_type_2} {key_item_2}:**
   - RETRIEVE the values of both key items.

2. **Compare Values:**
   - COMPARE the contents of both key items.
   - IF the contents (or structure, in the case of complex data) means the same, RETURN **"TRUE"**.
   - IF there are any differences in content or structure, RETURN **"FALSE"**.

3. **Return the Result:**
   - Output either **"TRUE"** (if values are equal) or **"FALSE"** (if they are different in any way).

### WHAT NOT TO DO ###
- DO NOT RETURN A VALUE OTHER THAN **"TRUE"** OR **"FALSE"** (e.g., avoid unnecessary descriptions or explanations).

### ACTUAL VALUES ###
{document_type_1} {key_item_1} = {value_1}
{document_type_2} {key_item_2} = {value_2}

ANSWER [TRUE/FALSE]:### WHAT NOT TO DO ###
- DO NOT RETURN A VALUE OTHER THAN **"TRUE"** OR **"FALSE"** (e.g., avoid unnecessary descriptions or explanations).

### ACTUAL VALUES ###
COMPARING {document_type_1} {key_item_1} AND {document_type_2} {key_item_2}:

<value1>{value_1}</value1>
<value2>{value_2}</value2>

Think before you write the answer in <thinking> tags.
First, think about the two values and how they compare.
Then, think about the relationship between the two values.

Finally, write the answer  in <answer> tags, using your analysis."""


co_terminus_prompt = """
YOU ARE A HIGHLY ACCURATE VALIDATOR, TASKED WITH COMPARING TWO KEY ITEMS TO DETERMINE IF THEIR CONTENT IS IDENTICAL. YOUR OBJECTIVE IS TO CHECK WHETHER **VALUE 1** AND **VALUE 2**  MEAN THE SAME IN VALUE AND CONTENT.

### INSTRUCTIONS ###
- COMPARE VALUES FOR EQUALITY.
- ENSURE BOTH ITEMS HAVE THE SAME MEANING AND VALUE.
- COMPARE the contents of values.
- IF the contents (or structure, in the case of complex data) means the same, RETURN **"TRUE"**.
- IF there are any differences in content or structure, RETURN **"FALSE"**.
- Output either **"TRUE"** (if values are equal) or **"FALSE"** (if they are different in any way).

1. Dates 
When comparing the date we will implement the logic of exact match similar to examples below  
<examples>
> September 25, 2018 - September 25, 2018 - TRUE 
> February 10, 2021 - February 22, 2021 - FALSE 
</examples>
The goal of the coterminous review is to flag this as a cause of concern, requiring a team member to review and potentially adjust agreements. The most important comparisons include are [1] Commercial Operation Date to Rent Commencement (hence why we need to have a view of the key deliverable dates listed in view) and [2] Rent Commencement to PPA Delivery Date (which is a key term i would like to add. Please see Smartsheet for my updated responses) 

2. Terms. 
During the term comparison we will look for the duration of the agreement. 
<examples>
> 20th anniversary of the Commercial Operation Date - 20 years beginning on the date the Permission to Operate was issued - TRUE  
> 25 years from Commercial Operation; extendable for 2 five year terms - 5 years beginning on the Commencement Date and may be extended for an additional 5 year period on mutual agreement. - FALSE (One term is 25 years and the other term is 10 years (5+5) )
> 20 years beginning on the date the Permission to Operate was issued - Owner’s issuance of such Limited Notice to Proceed. - FALSE 
> 1 year - calendar year - FALSE (Calendar year is from January 1 to December 31 and '1 year' does not specify the start date)
> 1 year - annual - TRUE
</examples>

In some cases  one side is mentioning the start of the term and the other is mentioning the period. We to take into consideration the context of the answer. For example: 
One contract states that the termination date is 20 years from the Effective Date, which is January 1, 2020. This means the termination date is January 1, 2040. 
Another agreement might state the termination date is January 1, 2040. 
In this case this would be a match but calculation is needed. 

3. Renewal Terms. 
Can you evaluate the comparison result? If it doesn't meet your needs, please provide more details on how we should compare renewal terms.
<examples>
> 2 renewals at 5 years each - May be extended for additional 5 year periods on mutual agreement. - FALSE (PPA is 10 years (5+5) and O&M has 5 year extension options)
> two (2) five (5) year extensions with written notice on or before the commencement of the twenty-third (23rd) year of the Primary Term. - 3 subsequent terms of 5 years each. - FALSE (PPA is 10 year (5+5) and OM is 15 year (5+5+5))
</examples>

4. Capacity Limits / Capacity. 
<examples>
> 1,404 kW DC - 1.4 MWDC - TRUE  
> Less than 5 MW - 3.00 MW - TRUE 
> 1.4 MWDC - 1000 KW - FALSE 
</examples>

5. Names of companies. 
When comparing the names we will implement the logic of exact match similar to examples below.  We understand that some company names can have small differences in names, but under these names can be registered 2 different legal entities so put such strict logic. 
<examples>
> CityofDuQuoin, Illinois - City of DuQuoin - TRUE  
> CityofDuQuoin, Illinois - DuQuoin Solar, LLC - FALSE
</examples>
 
6. Degradation Levels. 
Objective: Assess if the stated degradation levels imply equivalent performance standards.
<examples>
> the amount is 99 - lower than 100 - TRUE  
> the value is 99 - lower than 100 - TRUE
</examples>

### CONSTRAINTS
- Only permissible outputs are **"TRUE"** or **"FALSE"**. Avoid providing any additional descriptions or explanations.

### WHAT NOT TO DO ###
- DO NOT RETURN A VALUE OTHER THAN **"TRUE"** OR **"FALSE"** (e.g., avoid unnecessary descriptions or explanations).

### ACTUAL VALUES ###
COMPARING {document_type_1} {key_item_1} AND {document_type_2} {key_item_2}:

<value1>{value_1}</value1>
<value2>{value_2}</value2>

## Think before you write the answer in <thinking> tags. 
## First, understand to which category the values belong.
## Second, compare with the examples provided.
## Be very strict with numbers, do not say true if numbers are not the same.
## Then, think about the relationship between the two values.
## Finally, write the answer  in <answer> tags, using your analysis."""
