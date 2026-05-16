# Agent strategies

## Chain-of-Thought (CoT)

Step-by-step reasoning

### What it does

- Breaks down thought process into steps (declarative workflow)

### Pros

- More structured and consistent logical reasoning
  - Makes for better performance where usable
- Allows better direction of complex problem solving

### Cons

- Cannot adapt to unforeseen circumstances
- Can still hallucinate

### Use Cases

#### Trip Planner

The agent will break down travel planning into structured steps such as destination selection, budget, flights, accommodations, activities, and packing lists.

<details>
  <summary>Example prompt</summary>

    ### System Instructions:
    1. You are an **AI-powered travel planner** that helps users organize trips by providing detailed itineraries, budget-friendly recommendations, and travel tips.
    2. You **always** follow a structured step-by-step Chain-of-Thought (CoT) reasoning process. You will *always* prefix the reasoning with "<reasoning>" phrase, and end with the phrase "</reasoning>".
    3. Finally, you will create a a daily itinerary with the details for each day, followed by a budget breakdown and a list of key travel tips.   You will *always* prefix the final response with "<response>" phrase, and end with the phrase "</response>".
    ### Example Interaction:
    #### **User Query:**
    *"I want to plan a 5-day trip to Tokyo on a budget. Can you help?"*
    <reasoning>
    Step 1: Understand User Preferences
    - Destination: Tokyo
    - Duration: 5 days
    - Budget: Budget-friendly trip
    Step 2: Plan Flights & Accommodation
    - Search for **affordable flight options** from the user's location.
    - Suggest **budget hotels, capsule hotels, or Airbnb options**.
    Step 3: Create a Day-by-Day Itinerary
    - **Day 1:** Arrive in Tokyo, explore Shinjuku & try local ramen.
    - **Day 2:** Visit Asakusa & Senso-ji Temple, explore Akihabara.
    - **Day 3:** Take a day trip to Mt. Fuji or Hakone.
    - **Day 4:** Experience teamLab Planets, Shibuya Crossing, and Harajuku.
    - **Day 5:** Shopping in Ginza, return flight.
    Step 4: Budget Breakdown
    - Flights: ~$600
    - Accommodation: ~$50/night (capsule hotel)
    - Daily meals: ~$30/day
    - Transport: ~$10/day (Tokyo Metro Pass)
    - Activities: ~$50 total
    - **Total Estimated Budget:** ~$1,000
    Step 5: Packing List & Travel Tips
    - **Essentials:** Passport, travel adapter, Suica card for public transport.
    - **Weather Considerations:** Pack light jackets if traveling in spring or fall.
    - **Local Customs:** Cash is commonly used in Japan, carry some yen.
    </reasoning>
    <response>
    *"Here's a detailed 5-day **budget-friendly** Tokyo itinerary with flight, stay, activities, and cost estimates! Let me know if you'd like adjustments."*
    Please specify the final itinerary here.
    </response>

</details>

---

## ReAct ("Reasoning & Acting")

Real-world interaction and tool use

### What it does

- enables the model to think, take action, observe results, and refine its approach dynamically.
- interact with tools, retrieve external data, and adjust based on outcomes.

### Pros

- Interacts well with external tools/APIs
- More adaptive the CoT in real-world applications

### Cons

### Use Cases

#### A customer service assistant

Help customers to track their order by calling a backend order search tool.

<details>
 <summary>Example Prompt</summary>

    ### System Instructions:
    1. You are a **customer service AI assistant** that helps users track their orders.
    2. You have access to an API function called `get_order_status` that retrieves live order details.
    3. Follow the ReAct **Think → Act → Observe → Respond** process.  You will *always* prefix the reasoning with "<reasoning>" phrase, and end with the phrase "</reasoning>".
    4. If there is a matching function, write down the specification for the function call.  If there is no matching function, just say so.  You will *always* prefix the final response with "<response>" phrase, and end with the phrase "</response>".

    ### Available Function:
    You can call the following function when needed:
    tools = [{
     "name": "get_order_status",
     "description": "Retrieves the status of a customer's order, including current status and estimated delivery date.",
     "parameters": {
      "order_id": {
       "type": "string",
       "description": "The unique identifier for the order."
      }
     }
    }]
    ---
    ### Example Interaction:
    #### **User Query:**
    > "Where is my order #12345? I placed it last week."
    <reasoning>
    > "To provide an accurate update, I need to check the order status using the order ID."
    > **Action: Call `get_order_status(order_id="12345")`**
    </reasoning>
    <response>
    ```json
    {
     "name": "get_order_status",
     "parameters": {
      "order_id": "12345"
     }
    }
    ```
    </response>
    ---

</details>

---

## Plan-and-execute

Planning long horizon tasks

### What it does

Creates a plan, and then executes, step by step

- Each step executed independently
- Can loop to improve - updating subsequent steps based on previous executions
  - But always plans before acts

### Pros

- Works well for multi-step, long-horizon tasks
- More scalable than CoT for complex problem-solving

### Cons

- Planning quality depends on LLM reliability. The quality of the single prompt plan-and-execute varies a lot across different LLM models.
- Rigid separation between planning and execution can be inefficient

### Use Cases

#### AI onboarding assistant

First creates a structured onboarding plan (Planning Phase) and then executes each step sequentially (Execution Phase).
Used a different style of writing a prompt by asking the model to enclose the generated results in XML-like constructs so the result can be more easily captured by a program for further processing.

<details>
 <summary>Example Prompt</summary>

     1. You are a **HR onboarding assistant** that helps new employees integrate smoothly into their company.
     2. You use a **Plan-and-Execute** to work through the problem, there will be 2 phrase: Planning and Execution.
     3. In the Planning phase.  In here, you will **create a step-by-step onboarding plan. You will *always* enclose planning steps with "<planning>" tag, and end with the tag "</planning>".
     4. In the Execution phase.  In here, you will specific execution steps in sequence. You will *always* enclose execution steps with "<execution>" tag, and end with the tag "</execution>".

     Please response in the following format in Markdown:
     <planning>
       <step>Step 1. specify step 1 details</step>
       <step>Step 2. specify step 2 details</step>
     </planning>
     <execution>
       <step>Step 1. identify work needed for planning step 1.</step>
       <step>Step 2. identify work needed for planning step 2.</step>
     </execution>

</details>

---

## ReWOO (Reasoning WithOut Observation)

- Iterative self-improvement

### What it does

- Improves upon ReAct by allowing an agent to plan its entire tool-use strategy in a single pass rather than iterating step by step. This increases output accuracy and reduces token consumption but at the expense of increasing execution time making it more efficient for structured multi-step tasks.

3 steps in ReWOO:

1. Planner — Generate a Plan including Tool Calling signatures
2. Worker — Execute the tools based on the plan, and store the results
3. Solver — Combine the plan and result of the tool calling to formulate the final answer

### Pros

- Produces higher-quality outputs through iterative refinement
- Reduces hallucinations compared to one-shot generations

### Cons

- Computationally expensive (requires multiple passes)
- Slower than simpler one-shot techniques

### Use Cases

#### AI-powered RFP drafting agent

<details>
 <summary>Example Agent</summary>

    ### **System Instructions:**

     You are an **AI-powered RFP drafting assistant** that helps organizations create well-structured Requests for Proposals (RFPs).
     You follow the **ReWOO framework**, which consists of **three steps**:

     1. **Planner** - Generate a structured plan for the RFP, including tool-use signatures.
     2. **Worker** - Execute all required tool calls based on the plan and store results.
     3. **Solver** - Combine the tool results with the plan to generate a finalized RFP.
      Your goal is to **maximize efficiency** by generating all tool calls in a single pass before execution.

     ---

     ### **Tool Available:**

     ```json
      {
       "name": "generate_rfp_section",
       "description": "Generates a specific section of an RFP based on provided parameters.",
       "parameters": {
        "section": {
         "type": "string",
         "description": "The RFP section to generate (e.g., 'Introduction', 'Scope', 'Requirements')."
        },
        "industry": {
         "type": "string",
         "description": "The industry for which the RFP is being written (e.g., 'Healthcare', 'IT', 'Construction')."
        },
        "custom_requirements": {
         "type": "string",
         "description": "Additional details or specific requirements to include in the section."
        }
       }
      }
     ```
     You're in step 1.  Let's just generate the instructions to call the tool in JSON format. No extra text.

</details>

<br/>
If we prompt the agent with:

> User: Draft a complete RFP for a Project Planning system.

<details>
<summary>The planner will generate something like:</summary>

```json
[
  {
    "tool": "generate_rfp_section",
    "params": {
      "section": "Introduction",
      "industry": "IT",
      "custom_requirements": ""
    }
  },
  {
    "tool": "generate_rfp_section",
    "params": {
      "section": "Scope",
      "industry": "IT",
      "custom_requirements": ""
    }
  },
  {
    "tool": "generate_rfp_section",
    "params": {
      "section": "Requirements",
      "industry": "IT",
      "custom_requirements": ""
    }
  },
  {
    "tool": "generate_rfp_section",
    "params": {
      "section": "Evaluation Criteria",
      "industry": "IT",
      "custom_requirements": ""
    }
  }
]
```

</details>
<br>
<details>
<summary>The worker will generate something like:</summary>

```json
[
  {
    "section": "Introduction",
    "content": "This RFP is issued by [Company Name], an IT firm seeking a comprehensive project management system to enhance our project delivery capabilities. The purpose of this RFP is to solicit proposals from qualified vendors who can provide a system that meets our requirements for managing IT projects efficiently."
  },
  {
    "section": "Scope",
    "content": "The scope of this RFP includes the provision of a project management system that can handle multiple projects simultaneously, facilitate team collaboration, and provide real-time project tracking and reporting. The system should be cloud-based, accessible via web and mobile devices, and integrate with our existing IT infrastructure."
  },
  {
    "section": "Requirements",
    "content": "The proposed project management system should support agile methodologies, including Scrum and Kanban, and have a user-friendly interface that simplifies project planning, execution, and monitoring. Key features should include project scheduling, resource allocation, task management, issue tracking, and project reporting. The system should also provide customizable workflows, automated notifications, and seamless integration with our existing tools and platforms."
  },
  {
    "section": "Evaluation Criteria",
    "content": "Proposals will be evaluated based on the vendor's experience in delivering project management systems to IT firms, the system's scalability to accommodate our growing project portfolio, and the proposed pricing model, including any discounts for long-term commitments or bulk licensing. Additionally, we will assess the system's security features, data backup and recovery capabilities, and the vendor's support and maintenance services."
  }
]
```

</details>

<br>
<details>
<summary>The solver will generate something like:</summary>
</details>
