<template>
    <div id="user-avatar">

        <v-avatar color="red">
            <span class="white--text headline" :size="32" :title="username">{{ initials }}</span>
        </v-avatar>

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