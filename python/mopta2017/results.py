import plotly
import plotly.plotly as py
import plotly.figure_factory as ff
import mopta2017.auxiliar as aux
import mopta2017.input_data as data_import
import mopta2017.tests as tests
import arrow

solution_dir = r'C:\Users\Franco\Documents\Projects\baobab\mopta2017\results/'
data_dir = "../data/20170326/"

solution_file = "201705230608_p60_t25000_sgurobi_tight.pickle"
# solution_file = "201705070150_60_todo_gurobi.pickle"
data_in = data_import.get_data_clean(data_dir)
data_in['demand'] = aux.group_patients(data_in=data_in, period_size=60)
solution = aux.load_solution(solution_dir + solution_file)

sum(tests.get_costs(solution, data_in).values())
tests.check_solution(solution, data_in)

utc = arrow.utcnow().floor('day').shift(hours=7)

start_times = {key: utc.shift(minutes=min) for key, min in solution['jobs_start'].items()}
job_types = solution['jobs_type']
jobs = {job: data_in['production'][type] for job, type in solution['jobs_type'].items()}
end_times = {key: start_times[key].shift(minutes=value.time)  for key, value in jobs.items()}

veh_start_times = {key: utc.shift(minutes=min) for key, min in solution['routes_visit'].items()}
arcs = {arc: content for arc, content in aux.get_travel_arcs(solution['routes_visit']).items() if len(content)>1}
veh_end_times = {(key, element[0]): max(veh_start_times[(key, element[1])],
                                        veh_start_times[(key, element[0])].shift(minutes=data_in['travel'][element].times))
                 for key, value in arcs.items() for element in value}


df = [dict(Task=job[0],
           Start=start_times[job].format('YYYY-MM-DD HH:mm'),
           Finish=end_times[job].format('YYYY-MM-DD HH:mm'),
           Resource=job_types[job])
      for job in job_types.keys()
      ] + \
     [dict(Task=step[0][0]+5,
           Start=veh_start_times[step],
           Finish=veh_end_times[step],
           Resource=step[1])
      for step in veh_end_times.keys()
      ]

colors = {0: 'rgb(220, 0, 0)',
          1: (1, 0.9, 0.16),
          2: 'rgb(0, 255, 100)',
          3: 'rgb(120, 0, 50)',
          4: 'rgb(220, 0, 100)',
          5: 'rgb(0, 0, 255)',
          6: 'rgb(100, 50, 220)',
          7: 'rgb(220, 100, 220)'
          }

fig = ff.create_gantt(df, colors=colors, index_col='Resource', show_colorbar=True, group_tasks=True)
plotly.offline.plot(fig, filename='gantt-simple-gantt-chart.html')

