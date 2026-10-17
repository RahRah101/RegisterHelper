# RegisterHelper

RegisterHelper is a program that helps you register for courses faster.

# How it works

RegisterHelper reads the courses available for you using a platform adapter, as well as "enrichers" (RateMyProfessors, published professor/class grading statistics, Reddit posts).

RegisterHelper then reads your requirements + preferences (could be based on major/CPOS/goals/what you want/credit).

Using the constraints, enrichers and preferences, RegisterHelper builds ranked schedules and gives you the CRN list for each one, ready to paste into your school's registration page.

You can say things like "favor easiest professors with highest A percentage in their class" or "no classes before 10, keep Tuesday free" and RegisterHelper turns it into preferences you can review and adjust before it builds your schedules.

# Modes 
- Propose : RegisterHelper proposes you schedules + CRNs, you register yourself
- Watch : RegisterHelper checks seats on full classes and notifies you when a spot opens

# Architecture
## Adapters and Enrichers
RegisterHelper is modular. Each school plugs in through:
- Platform adapter: reads courses and sections from your school's platform (Banner, PeopleSoft, Workday, etc...). Most schools use one of these, so you probably don't need to write a new one, but you can if need be.
- School config: a small YAML file with your school's URLs, term codes, etc... 
- Enrichers: extra data about professors and classes (RateMyProfessors, grade distributions statistics, Reddit...)

For example with Georgia State University :
```yaml 
school: gsu
platform: banner9
base_url: ...
term_code: "{year}{08|01|05}
rmp_school_id: ...
grade_source: https://dssapex.gsu.edu/ords/f?p=140:184:20037969984046::::P_TERM_184:202508:
```

# Install / Usage 

TODO
