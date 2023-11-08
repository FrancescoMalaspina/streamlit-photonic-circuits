# Import necessary libraries
import streamlit as st
import numpy as np
import plotly.graph_objects as go
# from base import Pin, wavelength_to_frequency
# from headless_snowman import HeadlessSnowman
from src import Pin, wavelength_to_frequency, HeadlessSnowman
from scipy.constants import c

# structure parameters
main_radius = 120 * 1e-6
auxiliary_radius = 90 * 1e-6
mach_zender_length = 120 * np.pi * 1e-6
main_cross_coupling = 1e-1
auxiliary_cross_coupling = 3e-1

# propagation parameters
central_wavelength = 1.55e-6
effective_index = 1.7
group_index = 2
GVD = 0.6e-24
loss_dB = 10 # 10 dB/m

# simulation parameters
number_of_points = 10000
omega_0 = wavelength_to_frequency(1550e-9)
omega_m = c / auxiliary_radius / group_index
n_res = 5
angular_frequencies = np.linspace(omega_0 - n_res/2*omega_m, omega_0 + n_res/2*omega_m, number_of_points)

pin = 1 # TODO: make the pin choice an integer slider or something similar


# interactive plot with plotly
def interactive_plot(MZ_ratio, auxiliary_radius_ratio, new_main_cross_coupling, new_auxiliary_cross_coupling, log_scale, n_res_left, n_res_right): 
    angular_frequencies = np.linspace(omega_0 + n_res_left/2*omega_m, omega_0 + n_res_right/2*omega_m, number_of_points)
    # objects
    Pin.reset_id_iterator()
    standard_HS = HeadlessSnowman(
        main_radius = main_radius,
        auxiliary_radius = auxiliary_radius,
        mach_zender_length = mach_zender_length,
        input_cross_coupling_coefficient=main_cross_coupling,
        through_cross_coupling_coefficient=main_cross_coupling,
        ring_cross_coupling_coefficient= 0, 
        effective_refractive_index=effective_index,
        group_refractive_index=group_index,
        GVD=GVD,
        loss_dB=loss_dB,
        central_wavelength=central_wavelength,
        angular_frequencies=angular_frequencies,
    )
    Pin.reset_id_iterator()
    new_HS = HeadlessSnowman(
        main_radius = main_radius,
        auxiliary_radius = auxiliary_radius_ratio * main_radius,
        mach_zender_length = MZ_ratio * main_radius * np.pi,
        input_cross_coupling_coefficient=new_main_cross_coupling,
        through_cross_coupling_coefficient=new_main_cross_coupling,
        ring_cross_coupling_coefficient= new_auxiliary_cross_coupling,
        effective_refractive_index=effective_index,
        group_refractive_index=group_index,
        GVD=GVD,
        loss_dB=loss_dB,
        central_wavelength=central_wavelength,
        angular_frequencies=angular_frequencies,
    )
    # plot
    fig = go.Figure(
        layout=dict(
            width=2400,  # Width in pixels
            height=1350  # Height in pixels
        )
    )
    fig.add_trace(go.Scatter(x=angular_frequencies, y=np.abs(standard_HS.fields[:, pin]), mode='lines', name='reference', line=dict(color="#1f77b4", dash='dot', width=2)))
    fig.add_trace(go.Scatter(x=angular_frequencies, y=np.abs(new_HS.fields[:, pin]), mode='lines', name=f'HS signal', line=dict(color="#ff7f0e",  width=2)))
    fig.update_layout(title=f'Field enhancement spectrum @ pin {pin}', xaxis_title='Angular frequency [rad/s]', yaxis_title='Field enhancement', autosize=False, width=800, height=500, margin=dict(l=50, r=50, b=100, t=100, pad=4))
    if log_scale:
        fig.update_layout(yaxis_type="log")
    return fig


# Streamlit app
def app():
    st.set_page_config(layout='wide')
    st.title('Headless Snowman')

    # Create sliders in the sidebar
    log_scale                   = st.sidebar.toggle('Log scale', value=True)
    st.sidebar.latex(r"\text{Main radius } (R_1): " + f"{main_radius:.1e} \ m")
    MZ_ratio                    = st.sidebar.slider('MZ length ratio (MZ / R_1)', min_value=0., max_value=10., value=1., step=0.05)
    auxiliary_radius_ratio      = st.sidebar.slider('Auxiliary radius ratio (R_2 / R_1)', min_value=0.01, max_value=2., value=1., step=0.01)
    main_cross_coupling         = st.sidebar.slider('Main cross coupling ()', min_value=0., max_value=1., value=0.1, step=0.01)
    auxiliary_cross_coupling    = st.sidebar.slider('Auxiliary cross coupling', min_value=0., max_value=1., value=0., step=0.01)
    n_res_left, n_res_right     = st.sidebar.slider('X axis range [number of resonances]', min_value=-20., max_value=20., value=(-3., +3.), step=0.5)

    fig = interactive_plot(MZ_ratio, auxiliary_radius_ratio, main_cross_coupling, auxiliary_cross_coupling, log_scale, n_res_left, n_res_right)

    # Display the plot
    st.plotly_chart(fig, use_container_width=True)

# Run the app
if __name__ == '__main__':
    app()
