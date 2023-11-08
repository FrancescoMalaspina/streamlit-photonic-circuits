from .base import BaseStructure, CompositeStructure, Pin, wavelength_to_frequency
from collections.abc import Sequence
import numpy as np
import matplotlib.pyplot as plt
from scipy.constants import c


class Waveguide(BaseStructure):
    num_pins = 2
    num_equations = 1

    def __init__(
            self,
            length: float = 0,
            effective_refractive_index: float = 1,
            group_refractive_index: float = 1,
            GVD: float = 0,
            loss_dB: float = 10,  # dB/m
            central_wavelength: float = 1550e-9,
            angular_frequencies: Sequence[float] = [wavelength_to_frequency(1550e-9)],
            pins: Sequence[Pin] = None
    ):
        super().__init__(pins=pins)
        self.length = length
        self.effective_refractive_index = effective_refractive_index
        self.group_refractive_index = group_refractive_index
        self.GVD = GVD
        self.loss_dB = loss_dB
        self.central_wavelength = central_wavelength
        self.angular_frequencies = np.array(angular_frequencies)
        self.central_frequency = 2 * np.pi / central_wavelength * c

    @property
    def wavevector(self):
        """ Return the wavevector for the structure, expanded to the second order in the angular frequency."""
        zero_order_term = self.effective_refractive_index * self.central_frequency / c
        first_order_term = self.group_refractive_index * (self.angular_frequencies - self.central_frequency) / c
        second_order_term = 1 / 2 * self.GVD * np.power((self.angular_frequencies - self.central_frequency), 2)
        wavevector = zero_order_term + first_order_term + second_order_term
        return wavevector

    @property
    def field_equations(self):
        loss_amplitude_coefficient = np.exp(-self.loss_dB * np.log(10) / 20 * self.length)
        equations = [{
            self.pins[0]: -loss_amplitude_coefficient * np.exp(1j * self.wavevector * self.length),
            self.pins[1]: 1,
        }]
        return equations

    def __str__(self):
        """ Return a string representation of the Pin object. """
        return f"Waveguide {self.id}"


# TODO: refactor the Source class, input fields in more than one pin: input of a vector of amplitudes, phases, and pins
class Source(BaseStructure):
    num_pins = 1
    num_equations = 1

    def __init__(self, amplitude: np.complex128 = 1, phase: float = 0, pins: Sequence[Pin] = None):
        super().__init__(pins=pins)
        self.amplitude = amplitude
        self.phase = phase

    def __str__(self):
        """ Return a string representation of the Pin object. """
        return f"Source {self.id}"

    @property
    def field_equations(self):
        equations = [{self.pins[0]: 1}]
        return equations

    @property
    def ordinate_vector(self):
        """ Return the ordinate vector for a Source. """
        return [self.amplitude]


class DirectionalCoupler(BaseStructure):
    """
        Field Equations:
        The field equations for the point coupler are:
        ```
        \begin{bmatrix}
        \sigma & 1j\kappa & 1 & 0 \\
        1j\kappa & \sigma & 0 & 1
        \end{bmatrix}
        \begin{bmatrix}
        A_0 \\
        A_1 \\
        A_2 \\
        A_3
        \end{bmatrix}
        =
        \begin{bmatrix}
        0 \\
        0
        \end{bmatrix}
        ```
        where `A_0`, `A_1`, `A_2`, and `A_3` are the complex amplitudes of the fields at the four pins of the point coupler,
        and `sigma` and `kappa` are the self-coupling and cross-coupling coefficients of the point coupler, respectively.
        """
    num_pins = 4
    num_equations = 2

    def __init__(
            self,
            cross_coupling_coefficient: float = np.sqrt(3 / 4),
            self_coupling_phase: float = 0,
            cross_coupling_phase: float = np.pi / 2,
            pins: Sequence[Pin] = None
    ):
        super().__init__(pins=pins)
        self.kappa = cross_coupling_coefficient * np.exp(1j * cross_coupling_phase)
        self.sigma = np.sqrt((1 - np.power(cross_coupling_coefficient, 2))) * np.exp(1j * self_coupling_phase)

    def __str__(self):
        """ Return a string representation of the Pin object. """
        return f"DirectionalCoupler {self.id}"

    @property
    def field_equations(self):
        equations = [{
            self.pins[0]: self.sigma,
            self.pins[1]: self.kappa,
            self.pins[2]: -1
        }, {
            self.pins[0]: - np.conj(self.kappa),
            self.pins[1]: np.conj(self.sigma),
            self.pins[3]: -1
        }]
        return equations


class RingResonator(CompositeStructure):
    num_pins = 4
    num_equations = 3

    def __init__(
            self,
            radius=1e-6,
            cross_coupling_coefficient=np.sqrt(3 / 4),
            effective_refractive_index=1,
            group_refractive_index=1,
            GVD=0,
            loss_dB=10,  # dB/m
            central_wavelength=1550e-9,
            angular_frequencies=[c * 1e6],
            pins: Sequence[Pin] = None
    ):
        super().__init__(effective_refractive_index, group_refractive_index, GVD, loss_dB, central_wavelength,
                         pins, angular_frequencies)
        self.radius = radius
        self.cross_coupling_coefficient = cross_coupling_coefficient
        self.structures = [
            DirectionalCoupler(self.cross_coupling_coefficient, pins=self.pins),
            Waveguide(
                length=2 * np.pi * self.radius,
                effective_refractive_index=self.effective_refractive_index,
                group_refractive_index=self.group_refractive_index,
                GVD=self.GVD,
                loss_dB=self.loss_dB,
                central_wavelength=self.central_wavelength,
                angular_frequencies=self.angular_frequencies,
                pins=[self.pins[3], self.pins[1]]
            )
        ]

    def __str__(self):
        """ Return a string representation of the Pin object. """
        return f"RingResonator {self.id}"

    def plot_spectrum(self):
        plt.figure(figsize=(12, 7))
        plt.plot(self.angular_frequencies, self.transmission, label="simulated", linewidth=1)

        # theoretical curve
        omega_0 = wavelength_to_frequency(self.central_wavelength)
        phase = self.wavevector * self.radius * 2 * np.pi
        sigma = np.sqrt((1 - np.power(self.cross_coupling_coefficient, 2)))
        loss = np.exp(-self.loss_dB * np.log(10) / 20 * self.radius * 2 * np.pi)
        teo_transmission = (sigma ** 2 + loss ** 2 - 2 * sigma * loss * np.cos(phase)) / (
                    1 + (sigma * loss) ** 2 - 2 * sigma * loss * np.cos(phase))
        plt.plot(self.angular_frequencies, teo_transmission, label="theorical", linestyle=":", linewidth=3)
        plt.vlines(omega_0, 0, 1, label="omega_0", linestyle="--", linewidth=2, color="grey")

        plt.xlabel("Angular frequency [s-1]")
        plt.ylabel("Transmission")
        plt.title("Transmission spectrum")
        # plt.yscale("log")
        plt.legend()
        plt.grid()
        plt.show()


class AddDropFilter(CompositeStructure):
    num_pins = 8
    num_equations = 6

    def __init__(
            self,
            radius: float = 1e-6,
            input_cross_coupling_coefficient: float = 0.1,
            auxiliary_cross_coupling_coefficient: float = 0.1,
            effective_refractive_index: float = 1,
            group_refractive_index: float = 1,
            GVD: float = 0,
            loss_dB: float = 10,  # dB/m
            central_wavelength: float = 1550e-9,
            angular_frequencies: float = c * 1e6,
            pins: Sequence[Pin] = None
    ):
        super().__init__(effective_refractive_index, group_refractive_index, GVD, loss_dB, central_wavelength,
                         pins, angular_frequencies)
        self.radius = radius
        self.input_cross_coupling_coefficient = input_cross_coupling_coefficient
        self.auxiliary_cross_coupling_coefficient = auxiliary_cross_coupling_coefficient
        self.structures = [
            DirectionalCoupler(self.input_cross_coupling_coefficient, pins=self.pins[:4]),
            DirectionalCoupler(self.auxiliary_cross_coupling_coefficient, pins=self.pins[4:]),
            Waveguide(
                length=self.radius * np.pi,
                effective_refractive_index=self.effective_refractive_index,
                group_refractive_index=self.group_refractive_index,
                GVD=self.GVD,
                loss_dB=self.loss_dB,
                central_wavelength=self.central_wavelength,
                angular_frequencies=self.angular_frequencies,
                pins=[self.pins[3], self.pins[5]]
            ),
            Waveguide(
                length=self.radius * np.pi,
                effective_refractive_index=self.effective_refractive_index,
                group_refractive_index=self.group_refractive_index,
                GVD=self.GVD,
                loss_dB=self.loss_dB,
                central_wavelength=self.central_wavelength,
                angular_frequencies=self.angular_frequencies,
                pins=[self.pins[7], self.pins[1]]
            )
        ]

    def __str__(self):
        """ Return a string representation of the Pin object. """
        return f"AddDropFilter {self.id}"

    @property
    def field_enhancement(self):
        return np.abs(self.fields[:, 3])

    @property
    def transmission(self):
        return np.power(np.abs(self.fields[:, 6]), 2)

    def plot_spectrum(self):
        plt.figure(figsize=(12, 7))
        plt.plot(self.angular_frequencies, self.transmission, label="simulated", linewidth=1)

        # theoretical curve
        omega_0 = wavelength_to_frequency(self.central_wavelength)
        phase = self.wavevector * 2 * self.radius * np.pi
        sigma = np.sqrt((1 - np.power(self.input_cross_coupling_coefficient, 2)))
        sigma_aux = np.sqrt((1 - np.power(self.auxiliary_cross_coupling_coefficient, 2)))
        loss = np.exp(-self.loss_dB * np.log(10) / 20 * self.radius * 2 * np.pi)
        teo_transmission = (self.input_cross_coupling_coefficient * self.auxiliary_cross_coupling_coefficient) ** 2 \
                           / (1 + (sigma * sigma_aux * loss) ** 2 - 2 * sigma * sigma_aux * loss * np.cos(phase))
        plt.plot(self.angular_frequencies, teo_transmission, label="theorical", linestyle=":", linewidth=3)
        plt.vlines(omega_0, 0, 1, label="omega_0", linestyle="--", linewidth=2, color="grey")
        plt.xlabel("Angular frequency [s-1]")
        plt.ylabel("Transmission")
        # plt.ylabel("Field enhancement")
        plt.title("Transmission spectrum")
        # plt.yscale("log")
        plt.legend()
        plt.grid()
        plt.show()


def ring_degub():
    omega_0 = wavelength_to_frequency(1550e-9)
    omega_m = c / 120e-6
    angular_frequencies = np.linspace(omega_0 - 1.5 * omega_m, omega_0 + 1.5 * omega_m, 50000)
    ring = RingResonator(
        radius=120e-6,
        cross_coupling_coefficient=1e-1,
        effective_refractive_index=1.7,
        group_refractive_index=2,
        GVD=0.6e-24,
        loss_dB=10,
        central_wavelength=1550e-9,
        angular_frequencies=angular_frequencies,
    )
    ring.structures.append(Source(pins=[ring.pins[0]]))
    ring.plot_spectrum()


def add_drop_filter_debug():
    omega_0 = wavelength_to_frequency(1550e-9)
    omega_m = c / 120e-6
    angular_frequencies = np.linspace(omega_0 - 1.5 * omega_m, omega_0 + 1.5 * omega_m, 50000)
    filter = AddDropFilter(
        radius=120e-6,
        input_cross_coupling_coefficient=1e-1,
        auxiliary_cross_coupling_coefficient=1e-1,
        effective_refractive_index=1.7,
        group_refractive_index=2,
        GVD=0.6e-24,
        loss_dB=10,
        central_wavelength=1550e-9,
        angular_frequencies=angular_frequencies,
    )
    filter.structures.append(Source(pins=[filter.pins[0]]))
    filter.structures.append(Source(amplitude=0, pins=[filter.pins[4]]))
    # print(len(filter.field_equations))
    # print(filter.coefficient_matrix)
    # print(filter.ordinate_vector)
    filter.plot_spectrum()


if __name__ == "__main__":
    ring_degub()
    # add_drop_filter_debug()
    # ring_interferometer_debug()
