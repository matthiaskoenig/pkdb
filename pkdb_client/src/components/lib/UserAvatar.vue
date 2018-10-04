<template>
    <div id="user-avatar">
        <md-avatar class="md-avatar-icon md-small" :title="username">{{ initials }}</md-avatar>
        <!--
        <font-awesome-icon class="md-icon" icon="user-cog"/>
        <font-awesome-icon icon="user-edit"/>
        -->
    </div>
</template>

<script>
    export default {
        name: "UserAvatar",
        props: {
            user: {
                type: Object,
                required: true
            }
        },
        computed: {
            username() {
                return this.user.first_name + ' ' + this.user.last_name;
            },
            initials() {
                return this.user.first_name[0] + this.user.last_name[0];
            }
        }
    }
</script>

<style scoped>

</style>