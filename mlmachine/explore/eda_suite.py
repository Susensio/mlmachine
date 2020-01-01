import pandas as pd
from pandas.api.types import is_numeric_dtype, is_object_dtype
import numpy as np

import seaborn as sns
import squarify
import matplotlib.pyplot as plt
import matplotlib.ticker as tkr
import matplotlib.cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap

from statsmodels.stats.weightstats import ztest
from statsmodels.stats.proportion import proportions_ztest
from scipy import stats

from IPython.display import display_html

import os
import sys

from prettierplot.plotter import PrettierPlot
from prettierplot import style



def eda_cat_target_cat_feat(self, feature, level_count_cap=50, color_map="viridis", legend_labels=None):
    """
    documentation:
        description:
            produces exploratory data visualizations and statistical summaries for a object
            feature in the context of a object target.
        parameters
            feature : string
                feature to visualize.
            level_count_cap : int, default = 50
                maximum number of unique levels in feature. if the number of levels exceeds the
                cap then the feature is skipped.
            color_map : string specifying built_in matplotlib colormap, default = "viridis"
                colormap from which to draw plot colors.
            legend_labels : list, default=None
                class labels to be displayed in plot legend(s).
    """
    if (len(np.unique(self.data[self.data[feature].notnull()][feature].values)) < level_count_cap):

        ### data summaries
        # feature summary
        uni_summ_df = pd.DataFrame(columns=[feature, "count", "proportion"])
        unique_vals, unique_counts = np.unique(
            self.data[self.data[feature].notnull()][feature], return_counts=True
        )
        for i, j in zip(unique_vals, unique_counts):
            uni_summ_df = uni_summ_df.append(
                {
                    feature: i,
                    "count": j,
                    "proportion": j / np.sum(unique_counts) * 100,
                },
                ignore_index=True,
            )
        uni_summ_df = uni_summ_df.sort_values(by=["proportion"], ascending=False)

        if is_numeric_dtype(uni_summ_df[feature]):
            uni_summ_df[feature] = uni_summ_df[feature].astype("int64")

        # feature vs. target summary
        bi_df = pd.concat([self.data[feature], self.target], axis=1)

        bi_summ_df = (
            bi_df.groupby([feature] + [self.target.name])
            .size()
            .reset_index()
            .pivot(columns=self.target.name, index=feature, values=0)
        )

        single_index = pd.Index(legend_labels) if legend_labels is not None else pd.Index([i for i in bi_summ_df.columns.tolist()])
        bi_summ_df.columns = single_index
        bi_summ_df.reset_index(inplace=True)

        # calculate percent of 100 by class label
        prop_df = pd.concat([self.data[feature], self.target], axis=1)
        prop_df = prop_df.groupby([feature, self.target.name]).agg({self.target.name : {"count": "count"}})
        prop_df = prop_df.groupby(level=0).apply(lambda x: 100 * x / float(x.sum()))
        prop_df = prop_df.reset_index()

        multiIndex = prop_df.columns
        singleIndex = [i[0] for i in multiIndex.tolist()]
        singleIndex[-1] = "Count"
        prop_df.columns = singleIndex
        prop_df = prop_df.reset_index(drop=True)

        prop_df = pd.pivot_table(prop_df, values=["Count"], columns=[feature], index=[self.target.name], aggfunc={"Count": np.mean})
        prop_df = prop_df.reset_index(drop=True)

        multiIndex = prop_df.columns
        singleIndex = [i[1] for i in multiIndex.tolist()]
        prop_df.columns = singleIndex
        prop_df = prop_df.reset_index(drop=True)
        prop_df.insert(loc=0, column='Class', value=legend_labels)

        # execute z_test
        if len(np.unique(bi_df[bi_df[feature].notnull()][feature])) == 2:

            # total observations
            total_obs1 = bi_df[(bi_df[feature] == np.unique(bi_df[feature])[0])][
                feature
            ].shape[0]
            total_obs2 = bi_df[(bi_df[feature] == np.unique(bi_df[feature])[1])][
                feature
            ].shape[0]

            # total positive observations
            pos_obs1 = bi_df[
                (bi_df[feature] == np.unique(bi_df[feature])[0])
                & (bi_df[self.target.name] == 1)
            ][feature].shape[0]
            pos_obs2 = bi_df[
                (bi_df[feature] == np.unique(bi_df[feature])[1])
                & (bi_df[self.target.name] == 1)
            ][feature].shape[0]

            z, p_val = proportions_ztest(
                count=(pos_obs1, pos_obs2), nobs=(total_obs1, total_obs2)
            )

            stat_test_df = pd.DataFrame(
                data=[{"z_test statistic": z, "p_value": p_val}],
                columns=["z_test statistic", "p_value"],
                index=[feature],
            ).round(4)

            # display summary tables
            self.df_side_by_side(
                dfs=(uni_summ_df, bi_summ_df, prop_df, stat_test_df),
                names=["Feature summary", "Feature vs. target summary", "Target proportion", "Statistical test",],
            )
            if "percent_positive" in bi_summ_df:
                bi_summ_df = bi_summ_df.drop(["percent_positive"], axis=1)

        else:
            # display summary tables
            self.df_side_by_side(
                dfs=(uni_summ_df, bi_summ_df, prop_df),
                names=["Feature summary", "Feature vs. target summary", "Target proportion"],
            )
            if "percent_positive" in bi_summ_df:
                bi_summ_df = bi_summ_df.drop(["percent_positive"], axis=1)

        ### visualizations
        # set label rotation angle
        len_unique_val = len(unique_vals)
        avg_len_unique_val = sum(map(len, str(unique_vals))) / len(unique_vals)
        if len_unique_val <= 4 and avg_len_unique_val <= 12:
            rotation = 0
        elif len_unique_val >= 5 and len_unique_val <= 8 and avg_len_unique_val <= 8:
            rotation = 0
        elif len_unique_val >= 9 and len_unique_val <= 14 and avg_len_unique_val <= 4:
            rotation = 0
        else:
            rotation = 90

        # instantiate charting object
        p = PrettierPlot(chart_prop=15, plot_orientation="wide")

        # treemap plot
        ax = p.make_canvas(title="Category counts\n* {}".format(feature), position=131, title_scale=0.85)
        p.pretty_tree_map(
            counts=uni_summ_df["count"].values,
            labels=uni_summ_df[feature].values,
            colors=style.color_gen(name=color_map, num=len(uni_summ_df[feature].values)),
            alpha=0.8,
            ax=ax,
        )

        # bivariate plot
        ax = p.make_canvas(title="Category counts by target\n* {}".format(feature), position=132)
        p.pretty_facet_cat(
            df=bi_summ_df,
            feature=feature,
            label_rotate=rotation,
            color_map=color_map,
            bbox=(1.0, 1.22),
            alpha=0.8,
            legend_labels=legend_labels,
            ax=ax,
        )

        # percent of total
        ax = p.make_canvas(title="Target proportion by category\n* {}".format(feature), position=133)
        p.pretty_stacked_bar_h(
            df=prop_df.drop("Class", axis=1),
            bbox=(1.0, 1.22),
            legend_labels=legend_labels,
            color_map=color_map,
            alpha=0.8,
            ax=ax,
        )

        plt.show()


def eda_cat_target_num_feat(self, feature, color_map="viridis", legend_labels=None):
    """
    documentation:
        description:
            produces exploratory data visualizations and statistical summaries for a number
            feature in the context of a object target.
        parameters
            feature : string
                feature to visualize.
            color_map : string specifying built_in matplotlib colormap, default = "viridis"
                colormap from which to draw plot colors.
            legend_labels : list, default=None
                class labels to be displayed in plot legend(s).
    """
    # bivariate roll_up table
    bi_df = pd.concat([self.data[feature], self.target], axis=1)

    # bivariate summary statistics
    bi_summ_stats_df = pd.DataFrame(
        columns=["class", "count", "proportion", "mean", "std"]
    )

    for labl in np.unique(self.target):
        feature_slice = bi_df[bi_df[self.target.name] == labl][feature]

        bi_summ_stats_df = bi_summ_stats_df.append(
            {
                "class": labl,
                "count": len(feature_slice),
                "proportion": len(feature_slice) / len(bi_df[feature]) * 100,
                "mean": np.mean(feature_slice),
                "std": np.std(feature_slice),
            },
            ignore_index=True,
        )

    if legend_labels is not None:
        bi_summ_stats_df["class"] = legend_labels

    elif is_numeric_dtype(bi_summ_stats_df["class"]):
        bi_summ_stats_df["class"] = bi_summ_stats_df["class"].astype("int64")


    # display summary tables
    describe_df = pd.DataFrame(bi_df[feature].describe()).reset_index()
    describe_df = describe_df.append(
        {
            "index": "skew",
            feature: np.round(stats.skew(bi_df[feature].values, nan_policy="omit"), 5),
        },
        ignore_index=True,
    )
    describe_df = describe_df.append(
        {
            "index": "kurtosis",
            feature: stats.kurtosis(bi_df[feature].values, nan_policy="omit"),
        },
        ignore_index=True,
    )
    describe_df = describe_df.rename(columns={"index": ""})

    # execute z_test or t_test
    if len(np.unique(self.target)) == 2:
        s1 = bi_df[
            (bi_df[self.target.name] == bi_df[self.target.name].unique()[0])
            & (bi_df[feature].notnull())
        ][feature]
        s2 = bi_df[
            (bi_df[self.target.name] == bi_df[self.target.name].unique()[1])
            & (bi_df[feature].notnull())
        ][feature]
        if len(s1) > 30 and len(s2) > 30:
            z, p_val = ztest(s1, s2)

            stat_test_df = pd.DataFrame(
                data=[{"z_test statistic": z, "p_value": p_val}],
                columns=["z_test statistic", "p_value"],
                index=[feature],
            ).round(4)
        else:
            t, p_val = stats.ttest_ind(s1, s2)

            stat_test_df = pd.DataFrame(
                data=[{"t_test statistic": t, "p_value": p_val}],
                columns=["t_test statistic", "p_value"],
                index=[feature],
            ).round(4)
        self.df_side_by_side(
            dfs=(describe_df, bi_summ_stats_df, stat_test_df),
            names=["Feature summary", "Feature vs. target summary", "statistical test"],
        )
    else:
        self.df_side_by_side(
            dfs=(describe_df, bi_summ_stats_df),
            names=["Feature summary", "Feature vs. target summary"],
        )

    # instantiate charting object
    p = PrettierPlot(chart_prop=15, plot_orientation="wide")

    # univariate plot
    ax = p.make_canvas(
        title="Feature distribution\n* {}".format(feature),
        title_scale=0.85,
        position=141,
    )
    p.pretty_dist_plot(
        bi_df[(bi_df[feature].notnull())][feature].values,
        color=style.style_grey,
        y_units="f",
        ax=ax,
    )

    # probability plot
    ax = p.make_canvas(
        title="Probability plot\n* {}".format(feature),
        title_scale=0.85,
        position=142,
    )
    p.pretty_prob_plot(
        x=bi_df[(bi_df[feature].notnull())][feature].values,
        plot=ax
    )

    # bivariate histogram
    ax = p.make_canvas(
        title="Distribution by class\n* {}".format(feature),
        title_scale=0.85,
        position=143,
    )

    # generate color list
    color_list = style.color_gen(name=color_map, num=len(np.unique(self.target)))

    for ix, labl in enumerate(np.unique(bi_df[(bi_df[feature].notnull())][self.target.name].values)):
        p.pretty_dist_plot(
            bi_df[(bi_df[feature].notnull()) & (bi_df[self.target.name] == labl)][feature].values,
            color=color_list[ix],
            y_units="ffff",
            kde=True,
            legend_labels=legend_labels,
            alpha=0.7,
            bbox=(1.1, 1.22),
            ax=ax,
        )

    # boxplot histogram
    ax = p.make_canvas(
        title="Boxplot by class\n* {}".format(feature),
        title_scale=0.85,
        position=144,
    )
    p.pretty_box_plot_h(
        x=feature,
        y=self.target.name,
        data=bi_df,
        alpha=0.7,
        legend_labels=legend_labels,
        bbox=(1.0, 1.22),
        suppress_outliers=True,
        ax=ax
        )
    plt.show()


def eda_num_target_num_feat(self, feature, color_map="viridis"):
    """
    documentation:
        description:
            produces exploratory data visualizations and statistical summaries for a number
            feature in the context of a number target.
        parameters
            feature : string
                feature to visualize.
            color_map : string specifying built_in matplotlib colormap, default = "viridis"
                colormap from which to draw plot colors.
    """
    ### summary tables
    # define bivariate dataframe
    bi_df = pd.concat([self.data[feature], self.target], axis=1)

    bi_df[self.target.name] = bi_df[self.target.name].astype(float)

    # define summary tables
    describe_df = pd.DataFrame(bi_df[feature].describe()).reset_index()

    # instantiate charting object
    p = PrettierPlot(chart_prop=15, plot_orientation="wide")

    # if number variable has fewer than a set number of unique variables, represent variable
    # as a object variable vs. a number target variable
    if len(np.unique(bi_df[feature].values)) <= 20:

        describe_df = describe_df.rename(columns={"index": ""})

        # bivariate summary statistics
        bi_summ_stats_df = pd.DataFrame(
            columns=[feature, "count", "proportion", "mean", "std_dv"]
        )
        unique_vals, unique_counts = np.unique(
            self.data[self.data[feature].notnull()][feature], return_counts=True
        )
        for feature_val in np.unique(bi_df[feature].values):
            feature_slice = bi_df[
                (bi_df[feature] == feature_val) & (bi_df[feature].notnull())
            ][feature]

            bi_summ_stats_df = bi_summ_stats_df.append(
                {
                    feature: feature_val,
                    "count": len(feature_slice),
                    "proportion": len(feature_slice) / len(bi_df[feature]) * 100,
                    "mean": np.mean(feature_slice),
                    "std_dv": np.std(feature_slice),
                },
                ignore_index=True,
            )

        # display summary dataframes
        self.df_side_by_side(
            dfs=(describe_df, bi_summ_stats_df),
            names=["univariate stats", "bivariate stats"],
        )

        # set rotation angle
        len_unique_val = len(unique_vals)
        avg_len_unique_val = sum(map(len, str(unique_vals))) / len(unique_vals)
        if len_unique_val <= 4 and avg_len_unique_val <= 12:
            rotation = 0
        elif len_unique_val >= 5 and len_unique_val <= 8 and avg_len_unique_val <= 8:
            rotation = 0
        elif len_unique_val >= 9 and len_unique_val <= 14 and avg_len_unique_val <= 4:
            rotation = 0
        else:
            rotation = 90

        # univariate plot
        ax = p.make_canvas(title="univariate\n* {}".format(feature), position=131)
        p.pretty_bar_v(
            x=list(map(str, unique_vals.tolist())),
            counts=unique_counts,
            label_rotate=rotation,
            color=style.style_grey,
            y_units="f",
            ax=ax,
        )

        # regression plot
        ax = p.make_canvas(title="regression plot\n* {}".format(feature), position=132)
        p.pretty_reg_plot(
            x=feature,
            y=self.target.name,
            data=bi_df[bi_df[feature].notnull()],
            x_jitter=0.2,
            ax=ax,
        )

        # hide every other label if total number of levels is less than 5
        if len_unique_val <= 4:
            xmin, xmax = ax.get_xlim()
            ax.set_xticks(np.round(np.linspace(xmin, xmax, len_unique_val), 2))

        # bivariate box plot
        ax = p.make_canvas(
            title="box plot - faceted by\n* {}".format(feature), position=133
        )
        p.pretty_box_plot_v(
            x=feature,
            y=self.target.name,
            data=bi_df[bi_df[feature].notnull()],
            color=matplotlib.cm.get_cmap(name=color_map),
            # color=style.gen_cmap(
            #     len(unique_vals),
            #     [style.style_hex_mid[0], style.style_hex_mid[1], style.style_hex_mid[2]],
            # ),
            label_rotate=rotation,
            ax=ax,
        )

    # if number variable has greater than a set number of unique variables, represent variable
    # as a number variable vs. a number target variable
    else:

        # add skew and curtosis to describe_df
        describe_df = describe_df.append(
            {
                "index": "skew",
                feature: stats.skew(bi_df[feature].values, nan_policy="omit"),
            },
            ignore_index=True,
        )
        describe_df = describe_df.append(
            {
                "index": "kurtosis",
                feature: stats.kurtosis(bi_df[feature].values, nan_policy="omit"),
            },
            ignore_index=True,
        )
        describe_df = describe_df.rename(columns={"index": ""})

        # display summary dataframes
        display(describe_df)

        # univariate plot
        ax = p.make_canvas(
            title="dist/kde - univariate\n* {}".format(feature), position=131
        )
        p.pretty_dist_plot(
            bi_df[(bi_df[feature].notnull())][feature].values,
            color=style.style_grey,
            y_units="fffff",
            fit=stats.norm,
            x_rotate=45,
            ax=ax,
        )

        # probability plot
        ax = p.make_canvas(title="probability plot\n* {}".format(feature), position=132)
        p.pretty_prob_plot(x=bi_df[(bi_df[feature].notnull())][feature].values, plot=ax)

        # regression plot
        ax = p.make_canvas(title="regression plot\n* {}".format(feature), position=133)
        p.pretty_reg_plot(
            x=feature,
            y=self.target.name,
            data=bi_df[bi_df[feature].notnull()],
            x_jitter=0.1,
            x_rotate=45,
            ax=ax,
        )
    plt.show()


def eda_num_target_cat_feat(self, feature, level_count_cap=50, color_map="viridis"):
    """
    documentation:
        description:
            produces exploratory data visualizations and statistical summaries for a number
            feature in the context of a object target.
        parameters
            feature : string
                feature to visualize.
            level_count_cap : int, default = 50
                maximum number of unique levels in feature. if the number of levels exceeds the
                cap then the feature is skipped.
            color_map : string specifying built_in matplotlib colormap, default = "viridis"
                colormap from which to draw plot colors.
    """
    if (
        len(np.unique(self.data[self.data[feature].notnull()][feature].values))
        < level_count_cap
    ):

        ### summary tables
        # univariate summary
        uni_summ_df = pd.DataFrame(columns=[feature, "count", "proportion"])
        unique_vals, unique_counts = np.unique(
            self.data[self.data[feature].notnull()][feature], return_counts=True
        )
        for i, j in zip(unique_vals, unique_counts):
            uni_summ_df = uni_summ_df.append(
                {feature: i, "count": j, "proportion": j / np.sum(unique_counts) * 100},
                ignore_index=True,
            )
        uni_summ_df = uni_summ_df.sort_values(by=["proportion"], ascending=False)

        # bivariate summary
        bi_df = pd.concat([self.data[feature], self.target], axis=1)

        bi_df[self.target.name] = bi_df[self.target.name].astype(float)
        stats_dict = {
            "n": len,
            "median": np.nanmedian,
            "mean": np.nanmean,
            "std_dev": np.nanstd,
        }
        bi_summ_piv_df = pd.pivot_table(
            bi_df, index=feature, aggfunc={self.target.name: stats_dict}
        )
        multi_index = bi_summ_piv_df.columns
        single_index = pd.Index([i[1] for i in multi_index.tolist()])
        bi_summ_piv_df.columns = single_index
        bi_summ_piv_df.reset_index(inplace=True)

        # display summary tables
        self.df_side_by_side(
            dfs=(uni_summ_df, bi_summ_piv_df),
            names=["univariate summary", "bivariate summary"],
        )

        ### plots
        # instantiate charting object
        p = PrettierPlot(chart_prop=15, plot_orientation="wide")

        # univariate plot
        ax = p.make_canvas(title="univariate\n* {}".format(feature), position=121)

        # select error catching block for resorting labels
        try:
            sorted(unique_vals, key=int)
        except ValueError:
            pass
        else:
            # sort unique_vals/unique_counts for bar chart
            new_ix = [
                sorted(list(unique_vals), key=int).index(i) for i in list(unique_vals)
            ]
            unique_vals = np.array(sorted(list(unique_vals), key=int))
            unique_counts = np.array([y for x, y in sorted(zip(new_ix, unique_counts))])

            # sort temporary data frame for box plot
            bi_df[feature] = bi_df[feature].astype(int)

        # set rotation angle
        len_unique_val = len(unique_vals)
        avg_len_unique_val = sum(map(len, str(unique_vals))) / len(unique_vals)
        if len_unique_val <= 4 and avg_len_unique_val <= 12:
            rotation = 0
        elif len_unique_val >= 5 and len_unique_val <= 8 and avg_len_unique_val <= 7.0:
            rotation = 0
        elif len_unique_val >= 9 and len_unique_val <= 14 and avg_len_unique_val <= 6:
            rotation = 0
        else:
            rotation = 30

        p.pretty_bar_v(
            x=list(map(str, unique_vals.tolist())),
            counts=unique_counts,
            label_rotate=rotation,
            color=style.style_grey,
            y_units="f",
            ax=ax,
        )

        # hide every other label if total number of levels is greater than 40
        if len_unique_val > 40:
            n = 2
            [
                l.set_visible(False)
                for (i, l) in enumerate(ax.xaxis.get_ticklabels())
                if i % n != 0
            ]

        # bivariate box plot
        ax = p.make_canvas(
            title="faceted by target\n* {}".format(feature), position=122
        )
        p.pretty_box_plot_v(
            x=feature,
            y=self.target.name,
            data=bi_df[bi_df[feature].notnull()].sort_values([feature]),
            color=matplotlib.cm.get_cmap(name=color_map),
            label_rotate=rotation,
            ax=ax,
        )

        # hide every other label if total number of levels is greater than 40
        if len_unique_val > 40:
            n = 2
            [
                l.set_visible(False)
                for (i, l) in enumerate(ax.xaxis.get_ticklabels())
                if i % n != 0
            ]

        plt.show()


def df_side_by_side(self, dfs, names=[]):
    """
    documentation:
        description:
            helper function for displaying pandas DataFrames side by side in a
            notebook.
        parameters:
            dfs : list
                list of dfs to be displayed.
            names : list, default = []
                list of names to be displayed above dataframes.
    """
    html_str = ""
    if names:
        html_str += (
            "<tr>"
            + "".join(f'<td style="text_align:center">{name}</td>' for name in names)
            + "</tr>"
        )
    html_str += (
        "<tr>"
        + "".join(
            f'<td style="vertical_align:top"> {df.to_html(index=False)}</td>'
            for df in dfs
        )
        + "</tr>"
    )
    html_str = f"<table>{html_str}</table>"
    html_str = html_str.replace("table", 'table style="display:inline"')
    display_html(html_str, raw=True)
